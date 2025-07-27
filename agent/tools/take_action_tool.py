from tools.base_tool import ToolDefinition

TakeActionInputSchema = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Describe in detail the action you want to take. This could either be talking to a human, doing something (e.g. going somewhere) physically, or interacting with an object or the environment."
        }
    },
    "required": ["action"]
}


def take_action(input_data: dict) -> str:
    return (
        f"The following action has been registered and will be executed by the external systems module: {input_data['action']}.")


TakeActionToolDefinition = ToolDefinition(
    name="take_action",
    description=(
        "Act on the outside world by using the external systems module of your robotic body."
        "This tool allows you to take actions in the real world, such as moving, interacting with objects, or communicating with humans."
        "This is the only tool that can be used to take actions in the real world; all other tools will not affect the outside world."
    ),
    input_schema=TakeActionInputSchema,
    function=take_action
)
