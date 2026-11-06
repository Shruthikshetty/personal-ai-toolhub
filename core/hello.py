"""
Core logic for taking in a name and replying hello
this is a reference on how to handle core logic and how to wire it up
with , CLI , REST and STDIO , Skill
"""


def sayHello(name: str) -> str:
    return f"Hello {name or 'Guest'} from Personal Ai ToolKit"
