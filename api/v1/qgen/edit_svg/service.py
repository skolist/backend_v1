import logging
import os

import supabase
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class SVGEditError(Exception):
    pass


def edit_svg_prompt(svg_string: str, instruction: str) -> str:
    """Generate prompt for editing SVG based on natural language instruction."""
    return f"""You are an SVG editor assistant. Your task is to modify the \
given SVG based on the user's instruction.

## Current SVG:
```svg
{svg_string}
```

## User's Instruction:
{instruction}

## Rules:
1. ONLY output the modified SVG code, nothing else
2. Keep the SVG valid and well-formed
3. Preserve the overall structure unless instructed otherwise
4. For text changes, update the content inside <text> elements
5. For position changes (move, shift), adjust x/y coordinates appropriately
6. For color changes, update stroke/fill attributes
7. For size changes, update width/height/radius/coordinates
8. If the instruction is unclear, make your best interpretation
9. LaTeX math should be wrapped in $...$ (e.g., $\\theta$, $\\pi$, $\\frac{{a}}{{b}}$)
10. DO NOT add any explanation or markdown, just the raw SVG code starting with <svg

## Modified SVG:"""


class EditSVGService:
    @staticmethod
    async def edit_svg(
        gen_image_id: str,
        instruction: str,
        supabase_client: supabase.Client,
    ) -> dict:
        """
        Edit an SVG based on natural language instruction.

        Args:
            gen_image_id: UUID of the image in gen_images table
            instruction: Natural language instruction for editing
            supabase_client: Supabase client instance

        Returns:
            dict with updated svg_string
        """
        # 1. Fetch current SVG from gen_images
        logger.info(f"Fetching SVG for image {gen_image_id}")
        result = supabase_client.table("gen_images").select("*").eq("id", gen_image_id).execute()

        if not result.data:
            raise SVGEditError(f"Image with id {gen_image_id} not found")

        image_data = result.data[0]
        current_svg = image_data.get("svg_string")

        if not current_svg:
            raise SVGEditError("Image does not have an SVG string to edit")

        # 2. Generate prompt and call Gemini
        prompt = edit_svg_prompt(current_svg, instruction)

        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = await gemini_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[types.Part.from_text(text=prompt)],
                    config={
                        "temperature": 0.2,  # Lower temperature for more precise edits
                    },
                )

                # Extract SVG from response
                new_svg = response.text.strip()

                # Clean up response if it has markdown code blocks
                if new_svg.startswith("```"):
                    # Remove markdown code blocks
                    lines = new_svg.split("\n")
                    # Find start and end of code block
                    start_idx = 0
                    end_idx = len(lines)
                    for i, line in enumerate(lines):
                        if line.startswith("```") and i == 0:
                            start_idx = 1
                        elif line.startswith("```svg"):
                            start_idx = i + 1
                        elif line.startswith("```") and i > 0:
                            end_idx = i
                            break
                    new_svg = "\n".join(lines[start_idx:end_idx]).strip()

                # Validate it starts with <svg
                if not new_svg.startswith("<svg") and not new_svg.startswith("<?xml"):
                    logger.warning(
                        f"Attempt {attempt + 1}: Response doesn't look like SVG: {new_svg[:100]}"
                    )
                    continue

                # 3. Update in Supabase
                supabase_client.table("gen_images").update({"svg_string": new_svg}).eq(
                    "id", gen_image_id
                ).execute()

                logger.info(f"Successfully updated SVG for image {gen_image_id}")

                return {
                    "id": gen_image_id,
                    "svg_string": new_svg,
                    "gen_question_id": image_data.get("gen_question_id"),
                    "position": image_data.get("position"),
                }

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

        raise SVGEditError(f"SVG edit failed after {max_retries} retries") from last_exception
