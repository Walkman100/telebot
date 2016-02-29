def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# https://github.com/Walkman100/NumeralConverter/blob/17fe334fb34088fbd7c7c25ef31fba5df8961512/Python27/numeralconverter.py#L68
def checkAndReturnRomanNumeral(input):
    if is_number(input):
        if len(input) < 6:
            return(returnRomanNumeral(int(input)))
        else:
            return("no.")
    else:
        return("\"" + input + "\" is not an Arabic number!")

def returnRomanNumeral(number):
    returnString = ""
    if number > 1000:
        for i in range(1, (number // 1000) +1):
            returnString = returnString + "M"
        number = number - (number // 1000) * 1000
    while number > 900:
        number = number - 900
        returnString = returnString + "CM"
    
    while number > 500:
        number = number - 500
        returnString = returnString + "D"
    while number > 400:
        number = number - 400
        returnString = returnString + "CD"
    
    while number > 100:
        number = number - 100
        returnString = returnString + "C"
    while number > 90:
        number = number - 90
        returnString = returnString + "XC"
    
    while number > 50:
        number = number - 50
        returnString = returnString + "L"
    while number > 40:
        number = number - 40
        returnString = returnString + "XL"
    
    while number > 10:
        number = number - 10
        returnString = returnString + "X"
    while number > 9:
        number = number - 9
        returnString = returnString + "IX"
    
    while number > 5:
        number = number - 5
        returnString = returnString + "V"
    while number > 4:
        number = number - 4
        returnString = returnString + "IV"
    
    while number >= 1:
        number = number - 1
        returnString = returnString + "I"
    return('`' + returnString + '`')

def returnArabicNumber(RomanNumber):
    RomanNumber = RomanNumber.upper()
    for i in range(0, len(RomanNumber)):
        # https://stackoverflow.com/a/1228327/2999220
        if RomanNumber[i] == "I":   RomanNumber = RomanNumber[:i] + '1' + RomanNumber[i + 1:]
        elif RomanNumber[i] == "V": RomanNumber = RomanNumber[:i] + '2' + RomanNumber[i + 1:]
        elif RomanNumber[i] == "X": RomanNumber = RomanNumber[:i] + '3' + RomanNumber[i + 1:]
        elif RomanNumber[i] == "L": RomanNumber = RomanNumber[:i] + '4' + RomanNumber[i + 1:]
        elif RomanNumber[i] == "C": RomanNumber = RomanNumber[:i] + '5' + RomanNumber[i + 1:]
        elif RomanNumber[i] == "D": RomanNumber = RomanNumber[:i] + '6' + RomanNumber[i + 1:]
        elif RomanNumber[i] == "M": RomanNumber = RomanNumber[:i] + '7' + RomanNumber[i + 1:]
        else:
            return("\"" + RomanNumber[i] + "\" is not a valid Roman Numeral character!")
    # Now we have the roman number in arabic numbers (so we can use < and >), we just add it all
    ArabicNumber = 0
    RomanNumber = RomanNumber + "0" # Because loops, length calculation and next letter calculation
    for i in range(0, len(RomanNumber)):
        if i < len(RomanNumber) - 1 and RomanNumber[i] >= RomanNumber[i + 1]:
            if RomanNumber[i] == "1":   ArabicNumber = ArabicNumber + 1
            elif RomanNumber[i] == "2": ArabicNumber = ArabicNumber + 5
            elif RomanNumber[i] == "3": ArabicNumber = ArabicNumber + 10
            elif RomanNumber[i] == "4": ArabicNumber = ArabicNumber + 50
            elif RomanNumber[i] == "5": ArabicNumber = ArabicNumber + 100
            elif RomanNumber[i] == "6": ArabicNumber = ArabicNumber + 500
            elif RomanNumber[i] == "7": ArabicNumber = ArabicNumber + 1000
        elif i < len(RomanNumber) - 1:
            if RomanNumber[i] == "1":   ArabicNumber = ArabicNumber - 1
            elif RomanNumber[i] == "2": ArabicNumber = ArabicNumber - 5
            elif RomanNumber[i] == "3": ArabicNumber = ArabicNumber - 10
            elif RomanNumber[i] == "4": ArabicNumber = ArabicNumber - 50
            elif RomanNumber[i] == "5": ArabicNumber = ArabicNumber - 100
            elif RomanNumber[i] == "6": ArabicNumber = ArabicNumber - 500
            elif RomanNumber[i] == "7": ArabicNumber = ArabicNumber - 1000
    return('`' + str(ArabicNumber) + '`')