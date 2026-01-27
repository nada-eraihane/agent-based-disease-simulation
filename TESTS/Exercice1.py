class Person:
    def __init__(self, name):
        self.name = name
        self.health = "healthy"
        self.x = 0
        self.y = 0
        
    def move_right(self):
        self.x+=1
        print(f"{self.name} movet to position ({self.x}, {self.y})")
    def get_sick(self):
        self.health ="sick"
        print (f"{self.name} is now sick!")

emma = Person("Emma")
emma.move_right()
# emma.move_right()
# emma.get_sick()

kali = Person("Kali")
kali.move_right()
kali.move_right()
kali.get_sick()