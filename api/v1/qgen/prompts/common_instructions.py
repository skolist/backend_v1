COMMON_INSTRUCTIONS = """
    1] Latex should be always put inside $$ blocks, don't forget
    2] For fill in the blanks etc. spaces should use $\\_\\_$ (contained in the $$) not some text{{__}} wrapper, also raw \\_\\_ won't work, we need $\\_\\_$
    3] Ensure no two inline math expressions appear consecutively without text between them; always insert minimal natural language (at least space) between adjacent $…$ blocks to avoid KaTeX parse errors.
    4]  Never output HTML tags like <br>, <p>, <span>, etc.; return only plain text with \n for line breaks.

    Ex. If \\sin^2\\theta = \\frac{{1}}{{3}}, what is the value of \\cos^2\\theta : This is not acceptable
        If $\\sin^2\\theta = 0.6$, then $\\cos^2\\theta = \\_.$ : This is acceptable
"""