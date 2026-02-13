# ruff: noqa: E501
COMMON_INSTRUCTIONS = """
    1] Latex should be always put inside $<content>$ blocks, don't forget
    2] For fill in the blanks etc. spaces should use $\\_\\_$ (contained in the $$) not some text{{__}} wrapper, also raw \\_\\_ won't work, we need $\\_\\_$
    3] Ensure no two inline math expressions appear consecutively without text between them; always insert minimal natural language (at least space) between adjacent $…$ blocks to avoid KaTeX parse errors.
    4]  Never output HTML tags like <br>, <p>, <span>, etc.; return only plain text with \n for line breaks.
    5] Don't unnecessarily use display math ($$...$$); prefer inline math ($...$) for simple expressions to ensure better compatibility with KaTeX rendering. Display math results in larger, centered equations that may not render well in all contexts. Always prefer inline math unless the question explicitly requires a large, standalone equation.
    Ex. If \\sin^2\\theta = \\frac{{1}}{{3}}, what is the value of \\cos^2\\theta : This is not acceptable
        If $\\sin^2\\theta = 0.6$, then $\\cos^2\\theta = \\_.$ : This is acceptable
    6] For fill in the blank questions use $\\_\\_\\_ \\_$ (four blanks)
    7] For Match The Following Type questions, stricly telling, don't use any special bulleting / formatting for options like A), B) or 1) , 2) , just return the rows as plain text, the frontend will take care of setting numbers to the rows. And keep minimum of 4 rows in both columns, and only 2 columns, unless explicitely told for more columns
    8] For questions which have nested sub-questions or parts like a,b,c,d or 1,2,3,4 in them, use proper empty line spacing, otherwise it looks cluttered and hard to read. And always add a empty line between the main questions and the sub-questions or parts. And a new line does not mean \\n, it should be an actual empty line, so that the frontend can render it properly with good spacing. But don't put empty lines between sub-questions or parts, just between main question and sub-questions or parts.
"""
