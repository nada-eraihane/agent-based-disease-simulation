import random
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

people = []
for i in range(5):
    person = Person(f"Person{i}")
    person.x = random.randint(0, 10)
    people.append(people)

people[0].health = "sick"

for day in range(10):
    print(f"\n---Day {day} ---")

    for person in people:
        if random.random() > 0.5:
            person.move_right()

    for sick_person in people:
        if sick_person.health in people:
            for healthy_person in people:
                if healthy_person.health == "healthy":
                    sick_person.maybe_infect(healthy_person)
    sick_count = sum(1 for p in people if p.health == "sick")
    print(f"sick people: {sick_count}")
