class Person:
    def __init__(self, name):
        self.name = name
        self.health = "healthy"
        self.x = 0
        self.y = 0
        
    def move_right(self):
        self.x += 1

    def is_near(self, other_person):
        distance = abs(self.x - other_person.x) + abs(self.y - other_person.y)
        return distance <= 1
    
    def maybe_infect(self, other_person):
        if self.health == "sick" and other_person.health =="healthy":
            if self.is_near(other_person):
                other_person.health="sick"
                print(f"{self.name} infected {other_person.name}!")

emma = Person("Emma")
kali = Person("Kali")

emma.health = "sick"
emma.x = 5
kali.x = 7
emma.maybe_infect(kali)
print("health Kali:" + kali.health)