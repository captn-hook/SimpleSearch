from pydantic import BaseModel, Field

class Tools:
   # Notice the current indentation: Valves and UserValves must be declared as
   # attributes of a Tools, Filter or Pipe class. Here we take the
   # example of a Tool.
    class Valves(BaseModel):
       # Valves and UserValves inherit from pydantic's BaseModel. This
       # enables complex use cases like model validators etc.
       test_valve: int = Field(  # Notice the type hint: it is used to
            # choose the kind of UI element to show the user (buttons,
            # texts, etc).
            default=4,
            description="A valve controlling a numberical value"
            # required=False,  # you can enforce fields using True
        )
    pass
       # Note that this 'pass' helps for parsing and is recommended.

   # UserValves are defined the same way.
    class UserValves(BaseModel):
       test_user_valve: bool = Field(
           default=False, description="A user valve controlling a True/False (on/off) switch"
       )
       pass

    def __init__(self):
       self.valves = self.Valves()
       # Because they are set by the admin, they are accessible directly
       # upon code execution.
       pass

   # The  __user__ handling is the same for Filters, Tools and Functions.
    def test_the_tool(self, message: str, __user__: dict):
       """
       This is a test tool. If the user asks you to test the tools, put any
       string you want in the message argument.

       :param message: Any string you want.
       :return: The same string as input.
       """
       # Because UserValves are defined per user they are only available
       # on use.
       # Note that although __user__ is a dict, __user__["valves"] is a
       # UserValves object. Hence you can access values like that:
       test_user_valve = __user__["valves"].test_user_valve
       # Or:
       test_user_valve = dict(__user__["valves"])["test_user_valve"]
       # But this will return the default value instead of the actual value:
       # test_user_valve = __user__["valves"]["test_user_valve"]  # Do not do that!
       
       return message + f"\nThe user valve set value is: {test_user_valve}"
       