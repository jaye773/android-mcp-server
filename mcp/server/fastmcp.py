class FastMCP:
    """Minimal FastMCP stub that records registered tools."""

    def __init__(self, name: str):
        self.name = name
        self.registered_tools = {}

    def tool(self, description: str = ""):
        def decorator(func):
            self.registered_tools[func.__name__] = {
                "callable": func,
                "description": description,
            }
            return func

        return decorator

    async def run_stdio_async(self):
        raise RuntimeError("FastMCP stub cannot run stdio server in tests")
