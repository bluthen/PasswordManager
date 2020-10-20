import random

checklist = {"alpha": False, "special": False, "number": False, "upAlpha": False}


def gen_alpha():
    return chr(random.randrange(97, 123))


def gen_special():
    special = ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "+", "{", "}", "_", "=", "?", ",", ".", ":"]
    return special[random.randrange(0, 21)]


def gen_number():
    return random.randrange(0, 10)


def gen_up_alpha():
    return chr(random.randrange(65, 91))


def generate_password():
    done = False
    password = ""
    while not done:
        if len(password) > 8:
            if not checklist["alpha"]:
                checklist["alpha"] = True
                password += gen_alpha()
            elif not checklist["special"]:
                checklist["special"] = True
                password += gen_special()
            elif not checklist["number"]:
                checklist["number"] = True
                password += str(gen_number())
            elif not checklist["upAlpha"]:
                checklist["upAlpha"] = True
                password += gen_up_alpha()
            else:
                done = True
        else:
            ptype = random.randrange(0, 4)
            if ptype == 0:
                checklist["alpha"] = True
                password += gen_alpha()
            if ptype == 1:
                checklist["special"] = True
                password += gen_special()
            if ptype == 2:
                checklist["number"] = True
                password += str(gen_number())
            if ptype == 3:
                checklist["upAlpha"] = True
                password += gen_up_alpha()
    return password
