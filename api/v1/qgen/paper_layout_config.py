"""
Paper Layout Configuration
===========================
This file mirrors the CSS variables from frontend/apps/ai_paper_generator/src/index.css
Keep these values in sync when updating the frontend config.

All spacing values are in the same units as the CSS (rem = 16px base, mm for margins)
"""

# ============================================================================
# PAGE MARGINS (in mm) - Used by Playwright PDF generation
# These should match --paper-margin-*-mm in index.css
# ============================================================================
PAGE_MARGIN_TOP_MM = 5
PAGE_MARGIN_RIGHT_MM = 20
PAGE_MARGIN_BOTTOM_MM = 20
PAGE_MARGIN_LEFT_MM = 20

# Footer reserved height in px
FOOTER_HEIGHT_PX = 30


# ============================================================================
# HEADER SPACING
# ============================================================================
HEADER_MARGIN_BOTTOM = "1.0rem"  # --header-margin-bottom
HEADER_LOGO_HEIGHT = "4rem"  # --header-logo-height (64px)
HEADER_LOGO_MARGIN_BOTTOM = "0.5rem"  # --header-logo-margin-bottom (8px)
HEADER_TITLE_MARGIN_TOP = "0.25rem"  # --header-title-margin-top (4px)
HEADER_META_MARGIN_TOP = "1rem"  # --header-meta-margin-top (16px)
HEADER_META_PADDING_Y = "0.5rem"  # --header-meta-padding-y (8px)
HEADER_META_GAP = "0.25rem"  # --header-meta-gap (4px)


# ============================================================================
# INSTRUCTIONS SPACING
# ============================================================================
INSTRUCTIONS_MARGIN_BOTTOM = "0.5rem"  # --instructions-margin-bottom (8px)
INSTRUCTIONS_PADDING_BOTTOM = "0rem"  # --instructions-padding-bottom
INSTRUCTIONS_TITLE_MARGIN_BOTTOM = "0.25rem"  # --instructions-title-margin-bottom (4px)
INSTRUCTIONS_LIST_PADDING_LEFT = "1.25rem"  # --instructions-list-padding-left (20px)
INSTRUCTIONS_ITEM_GAP = "0.25rem"  # --instructions-item-gap (4px)


# ============================================================================
# SECTION HEADER SPACING
# ============================================================================
SECTION_MARGIN_TOP = "0.5rem"  # --section-margin-top
SECTION_MARGIN_BOTTOM = "0.5rem"  # --section-margin-bottom


# ============================================================================
# QUESTION/ANSWER SPACING
# ============================================================================
QUESTION_MARGIN_BOTTOM = "0rem"  # --question-margin-bottom
QUESTION_FLEX_GAP = "0.5rem"  # --question-flex-gap (8px)
QUESTION_IMAGES_MARGIN_Y = "0.5rem"  # --question-images-margin-y (8px)
QUESTION_IMAGES_GAP = "0.5rem"  # --question-images-gap (8px)


# ============================================================================
# MCQ OPTIONS SPACING
# ============================================================================
OPTIONS_MARGIN_TOP = "0.5rem"  # --options-margin-top (8px)
OPTIONS_GAP_X = "1rem"  # --options-gap-x (16px)
OPTIONS_GAP_Y = "0.5rem"  # --options-gap-y (8px)


# ============================================================================
# MATCH THE FOLLOWING SPACING
# ============================================================================
MATCH_MARGIN_TOP = "1rem"  # --match-margin-top (16px)
MATCH_GAP_X = "2rem"  # --match-gap-x (32px)
MATCH_GAP_Y = "0.5rem"  # --match-gap-y (8px)


# ============================================================================
# ANSWER ITEM SPACING
# ============================================================================
ANSWER_MARGIN_BOTTOM = "1rem"  # --answer-margin-bottom (16px)
ANSWER_EXPLANATION_MARGIN_TOP = "0.5rem"  # --answer-explanation-margin-top (8px)


# ============================================================================
# HELPER: Get margin dict for Playwright PDF options
# ============================================================================
def get_pdf_margins():
    """Returns margin dict for Playwright's pdf_options"""
    return {
        "top": f"{PAGE_MARGIN_TOP_MM}mm",
        "right": f"{PAGE_MARGIN_RIGHT_MM}mm",
        "bottom": f"{PAGE_MARGIN_BOTTOM_MM}mm",
        "left": f"{PAGE_MARGIN_LEFT_MM}mm",
    }
