import re


def insert_sections_in_markdown(content: str, section: str, position: str = "end") -> str:
    """Insert markdown `section` into `content` at the specified position."""
    if position == "after_intro":
        # Find the first heading (H1 or H2)
        match = re.search(r"^#{1,2} .*$", content, flags=re.MULTILINE)
        if match:
            insert_pos = match.end()
            # advance past any following blank lines
            after = re.search(r"\n\s*\n", content[insert_pos:])
            if after:
                insert_pos += after.end()
        else:
            insert_pos = 0
        return content[:insert_pos].rstrip() + "\n\n" + section.strip() + "\n\n" + content[insert_pos:].lstrip()
    else:
        return content.rstrip() + "\n\n" + section.strip() + "\n"
