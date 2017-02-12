import random

checklist = {"alpha":False, "special":False, "number":False, "upAlpha":False}

def genAlpha():
    return chr(random.randrange(97, 123));

def genSpecial():
    special=["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "+", "{", "}", "_", "=", "?", ",", ".",":"];
    return special[random.randrange(0, 21)]

def genNumber():
    return random.randrange(0, 10)

def genUpAlpha():
    return chr(random.randrange(65,91))

def generatePassword():
    done = False
    password = ""
    while (not done):
        if (len(password) > 8):
            if ( not checklist["alpha"] ):
                checklist["alpha"] = True
                password += genAlpha()
            elif ( not checklist["special"] ):
                checklist["special"] = True
                password += genSpecial()
            elif ( not checklist["number"] ):
                checklist["number"] = True
                password += str(genNumber())
            elif ( not checklist["upAlpha"] ):
                checklist["upAlpha"] = True
                password += genUpAlpha()
            else:
                done = True
        else:
            type = random.randrange(0, 4)
            if ( type == 0 ):
                checklist["alpha"] = True
                password += genAlpha()
            if ( type == 1 ):
                checklist["special"] = True
                password += genSpecial()
            if ( type == 2 ):
                checklist["number"] = True
                password += str(genNumber())
            if ( type == 3 ):
                checklist["upAlpha"] = True
                password += genUpAlpha()
    return password
    
