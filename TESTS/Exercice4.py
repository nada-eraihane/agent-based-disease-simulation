import random

class Person:
    def __init__(self, name):
        self.name = name
        state = ["healthy", "sick"]
        self.health = random.choice(state)
        self.x = random.randint(0,10)
        self.y = random.randint(0,10)
        

    def move(self):
        a= random.choice([-1, 0, 1])
        b= random.choice([-1, 0, 1])
        self.x += a
        self.y += b
        print(self.x,self.y)

    def is_near(self, other_person):
        distance = abs((self.x - other_person.x) + (self.y - other_person.y))
        return distance <= 1
    
    def maybe_infect(self, other_person):
        if self.health == "sick" and other_person.health == "healthy":
            if self.is_near(other_person):
                other_person.health= "sick"
                print(f"{self.name} infected {other_person.name}!")

    
people = []

for i in range(5):
    person = Person(f"Person{i}")
    people.append(person)
    print(f"{person.name}:{person.health}")

for day in range(10):
    print(f"Day {day}:")
    for person in people:
        person.move()

for sick_person in people:
    if sick_person.health == "sick":
        for healthy_person in people:
            if healthy_person.health == "healthy":
                sick_person.maybe_infect(healthy_person)

        
for person in people:
    print(f"{person.name}:{person.health}")   
    
