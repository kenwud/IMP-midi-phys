import pymunk
print(f"Pymunk version: {pymunk.version}")
space = pymunk.Space()
print("Methods in pymunk.Space:")
print([m for m in dir(space) if "collision" in m.lower()])
