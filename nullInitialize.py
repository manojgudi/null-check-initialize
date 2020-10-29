#!/usr/bin/python3

import argparse
import re
import os

printInColor = True
try:
    import colorama
    from colorama import Fore, Style
except:
    print("Didn't find colorama library, install it using pip. Disabling color")
    printInColor = False

########## UTILITY CLASS ##############
def readFileContents(qualifiedFilename):
    """
    Read file contents and apply
    """
    return open(qualifiedFilename).read()

def getGreenText(text, shouldPrint=True):
    """
    print text in green
    """
    if not printInColor:
        print(text)
        return

    greenText = Fore.GREEN + text + Style.RESET_ALL
    if shouldPrint:
        print(greenText)

    return greenText
    #print(f"{Fore.GREEN}Heeloo{Style.RESET_ALL}")

def getRedText(text, shouldPrint=True):
    """
    print text in red
    """
    if not printInColor:
        print(text)
        return

    redText = Fore.RED + text + Style.RESET_ALL
    if shouldPrint:
        print(redText)

    return redText

def getBlueText(text, shouldPrint=True):
    """
    print text in red
    """
    if not printInColor:
        print(text)
        return

    blueText = Fore.BLUE  + text + Style.RESET_ALL
    if shouldPrint:
        print(blueText)

    return blueText



def writeFileContents(filePath, fileText):
    """
    filePath
    """
    fileName, fileExtension = filePath.split(".")
    fileName += "_GENERATED"
    filePath_ = fileName + "." + fileExtension
    fileHandler = open(filePath_, "w")
    fileHandler.write(fileText)
    fileHandler.close()


#######################################
class DependencyObject:
    def __init__(self, dependencyMap, line, lValue):
        self.dependencyMap = dependencyMap
        self.line          = line
        self.lValue        = lValue

class SearchSpaceTextClass:
    def __init__(self, searchSpaceText, lineNumber, startCharIndex, endCharIndex):
        self.searchSpaceText = searchSpaceText
        self.lineNumber      = lineNumber
        self.startCharIndex  = startCharIndex
        self.endCharIndex    = endCharIndex

def replaceAllNewline(line ):
    while (line.find("\n") != -1):
        line = line.replace('\n', ' ')

    return line

def preProcessText(text):
    """
    1. Remove trailing whitespace
    2. Linearize
    """
    text = text.strip()

    delimitedLines = []


    for line in text.split(";"):
        line = line.strip() + "; "

        # Find \n and replace for that line
        line = replaceAllNewline(line)

        # NOTE Tricky hack for open-paranthesis
        if line.find("{") > -1:
            for subline in line.split("{"):
                subline = subline.strip() + "{"
                delimitedLines.append(subline)

            continue

        delimitedLines.append(line)
    return delimitedLines


def findVariableLHSInLine(line):
    """
    Find the LValue 
    """
    # Since the line is preprocessed, simply return the first instance of Variable a
    #print(line)
    variableRegex = re.compile('\$([a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*).+?(?=\=)')
    variableList  = variableRegex.findall(line)
    # If lvalueList is empty, then exit
    if not variableList:
        return 

    #print("Variable List", variableList)   
    return "$"+variableList[0]

def findVariableRHSInLine(line):
    """
    find all the variables which are on RHS
    """
    # Find "=" and not "=="
    equalToIndex = line.find("=")
    if equalToIndex == -1:
        print("No variables found on RHS")
        return
    # If "=" is not the last char of the line OR if there is another "=" present
    if (len(line) == equalToIndex+1) or (line[equalToIndex+1] == "="):
        #print("== found so ignoring")
        return

    # Split the line from the first equalTo symbol
    rightLine = line[equalToIndex+1:]
    # Find the variables
    variableRegex = re.compile('\$([a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*)')
    variableList  =  set([ "$"+x for x in variableRegex.findall(rightLine)  ])
    return variableList

def buildVariableDependenceMap(line):
    """
    Returns a Map of form:
        { LValue : Set Of RHS Variables }
    """

    lValue = findVariableLHSInLine(line)
    if not lValue:
        #print("No LValue Found in this Line")
        return

    rValueSet = findVariableRHSInLine(line)

    if not rValueSet:
        # lValue is not a daughter variable, either a constant or a function call
        return 

    # Remove self-instance from the set for the cases lValue = lValue + 1
    rValueSet.discard(lValue)

    dependencyMap = { lValue : rValueSet }

    dependencyObject = DependencyObject(dependencyMap, line, lValue)

    return dependencyObject


def buildInitializationStatements(variableOfInterest, dependencyMap, 
            delimitedLines, delimitedLinesEntireText, searchSpaceTextObject, fileText, nullCheck=True):
    """
    Generate code with null initialization
    """

    rValuesSet = dependencyMap.get(variableOfInterest, [])
    if not rValuesSet:
        print("OOPS variableOfInterest not found in dependencyMap | Send Manoj the file name and debug line below:\n\n")
        print("--------------COPY--------------\n")
        print(dependencyMap)
        print("Variable Of Interest", variableOfInterest)
        print("\n--------------END COPY-------------")
        return

    # CASE 1 parent initialization | parent null check
    daughterVariables = findDaughterVariables(variableOfInterest, dependencyMap)

    # Check if variable of interest and its daughter variables are initialized to null or not.
    variablesToCheck = list(daughterVariables)
    variablesToCheck.append(variableOfInterest)
    for variableToCheck in variablesToCheck:

        # count line from start of the file to the first instance of the variableToCheck first found in the searchSpaceText
        variableFirstFound       = searchSpaceTextObject.searchSpaceText.find(variableToCheck)
        variableFirstFoundInFile = searchSpaceTextObject.startCharIndex + variableFirstFound
        lineNumberVariable       = fileText[0:variableFirstFoundInFile].count("\n") + 1

        # NOTE Fix lineCountActual
        lineCountActual, isVariableInitialized_ = isVariableInitialized(variableToCheck,
                                                        delimitedLinesEntireText)
        if isVariableInitialized_:
            getBlueText("=> Variable %s is initialized with null on line "%(variableToCheck))
        else:
            getRedText("=> Variable %s is NOT initialized with null on line %s "%(variableToCheck, lineNumberVariable))


    return placeNullInitialization(variableOfInterest, daughterVariables, \
                    delimitedLines, searchSpaceTextObject)


def findDaughterVariables(variableOfInterest, dependencyMap):
    """
    Build Inverse Dependency Map assuming variableOfInterest as the root 
    """
    daughterVariables = []
    for lValue, rValueSet in dependencyMap.items():
        if variableOfInterest in rValueSet:
            daughterVariables.append(lValue)

    return daughterVariables


def isVariableInitialized(lValue, delimitedLines):
    """
    Check if the lvalue has been initialized with null value
    If yes, which line
    """
    lineCount              = 0
    isVariableInitialized_ = False

    # If the lValue exists
    for line in delimitedLines:
        lineCount += 1
        if (line.find("null") != -1) and (line.find(lValue) != -1):
            #print("Initialized here ", line)
            isVariableInitialized_ = True

    # Figure out lineCount on delimitedLines is lineCount when delimited by \n
    text_ = ""
    for line in delimitedLines[:lineCount+1]:
        text_ += line

    lineCountActual = text_.count("||")
    return (lineCountActual, isVariableInitialized_)

def generateNullInitialized(lValue):
    """
    For lValue initialize it
    """
    return "\n    %s = null; //NOTE Auto-generated initialization"%lValue


def placeNullInitialization(lValue, daughterVariables, delimitedLines, searchSpaceTextObject):
    """
    places null initialization statement before the first instance of the lvalue
    """

    fileText          = searchSpaceTextObject.searchSpaceText
    lineNumber        = searchSpaceTextObject.lineNumber

    firstInstanceLine = 0
    # To Print
    initializationStatement      = generateNullInitialized(lValue)

    for line in delimitedLines:
        # Found the first instance where lvalue was used
        if line.find(lValue) != -1:
            break

        firstInstanceLine += 1

    delimitedLinesWithoutPreprocessing = fileText.split(";")
    # Place if properly
    if firstInstanceLine == 0:
        delimitedLinesWithoutPreprocessing.insert(0, initializationStatement)
    else:
        delimitedLinesWithoutPreprocessing.insert(firstInstanceLine-1, initializationStatement)

    fileTextWithNullInitialization = ""
    for line in delimitedLinesWithoutPreprocessing[:-1]:
        fileTextWithNullInitialization += line + ";"

    ### TO PRINT
    initializationStatementPrint = getGreenText(generateNullInitialized(lValue), False)
    delimitedLinesWithoutPreprocessing = fileText.split(";")
    # Place if properly
    if firstInstanceLine == 0:
        delimitedLinesWithoutPreprocessing.insert(0, initializationStatementPrint)
    else:
        delimitedLinesWithoutPreprocessing.insert(firstInstanceLine-1, initializationStatementPrint)

    fileTextWithNullInitializationPrint = ""
    for line in delimitedLinesWithoutPreprocessing[:-1]:
        if line:
            fileTextWithNullInitializationPrint += line + ";"


    # Append last line without colon
    fileTextWithNullInitialization += delimitedLinesWithoutPreprocessing[-1]

    # If there are no daughter variables
    if not daughterVariables:
        getGreenText("\n\n@@@@ Adding it on line: %s"%str(lineNumber))
        print(fileTextWithNullInitializationPrint)
        return fileTextWithNullInitialization

    # For daughterVariables
    daughterLinesToBeRemoved = [] # These are also the lines which will be inside null check
    nullCheckBlock = "\n\t\\\\NOTE Auto-generated if Block\n    if (%s){\n%s    }"%(lValue, "      %s\n"*len(daughterVariables))
    for daughterVariable in daughterVariables:
        for line in delimitedLines:
            if line.find(daughterVariable) != -1:
                daughterLinesToBeRemoved.append(line.strip())
                break

    # No daughterVariables found then leave everything as it is
    if not daughterLinesToBeRemoved:
        print(fileTextWithNullInitialization)
        return fileTextWithNullInitialization

    # Prepare null check block
    nullCheckBlock = nullCheckBlock % tuple(daughterLinesToBeRemoved)
    nullCheckBlockInsertionPlace = fileTextWithNullInitialization.find(
                                        daughterLinesToBeRemoved[0])

    for daughterLineToBeRemoved in daughterLinesToBeRemoved:
        fileTextWithNullInitialization       = fileTextWithNullInitialization.replace(daughterLineToBeRemoved, "")
        fileTextWithNullInitializationPrint  = fileTextWithNullInitializationPrint.replace(daughterLineToBeRemoved, "")

    ### TO PRINT 
    fileTextWithNullInitializationPrint = fileTextWithNullInitializationPrint[:nullCheckBlockInsertionPlace] \
                                      + "\n " + getGreenText(nullCheckBlock, False) \
                                      + fileTextWithNullInitializationPrint[nullCheckBlockInsertionPlace:]

    fileTextWithNullInitialization  = fileTextWithNullInitialization[:nullCheckBlockInsertionPlace] \
                                      + "\n " + nullCheckBlock \
                                      + fileTextWithNullInitialization[nullCheckBlockInsertionPlace:]


    getGreenText("\n\n@@@@ Adding it on line: %s"%str(lineNumber))
    print(fileTextWithNullInitializationPrint)
    return fileTextWithNullInitialization

def getStartOfTheLine(keyPhraseOccurenceIndex, fileText, delimiter = ";"):
    return fileText[:keyPhraseOccurenceIndex].rfind(delimiter)

def getLineNumber(startIndex, fileText):
    """
    Get the number of line where search space text starts
    """
    return fileText[:startIndex].count("\n") - 1

def getSearchSpaceText(fileText, keyPhrase):
    """
    Takes the entire file content, finds all occurences of keyphrase
    and narrows down the search space where the script
    should look for daughter variables
    """
    keyPhraseOccurenceIndexes = [x.start() for x in re.finditer(keyPhrase, fileText)]

    searchSpaceTexts = []
    for keyPhraseOccurenceIndex in keyPhraseOccurenceIndexes:
        searchSpaceText = ""
        requiredEndParanthesis = 0 
        charCount              = 0 

        for char in fileText[keyPhraseOccurenceIndex : ]:
            charCount += 1
            if char == "{":
                # Subtract 1 
                requiredEndParanthesis += -1

            if char == "}":
                requiredEndParanthesis += 1

            # Found exactly 1 NET end paranthesis
            if requiredEndParanthesis == 1:
                getStartOfTheLineIndex = getStartOfTheLine(keyPhraseOccurenceIndex,
                    fileText)
                startCharIndex            = getStartOfTheLineIndex+1
                endCharIndex              = keyPhraseOccurenceIndex+charCount
                searchSpaceText           = fileText[startCharIndex:endCharIndex]
                searchSpaceTextLineNumber = getLineNumber(keyPhraseOccurenceIndex, fileText)
                searchSpaceTextObject = SearchSpaceTextClass(searchSpaceText, 
                    searchSpaceTextLineNumber, startCharIndex, endCharIndex)

                searchSpaceTexts.append(searchSpaceTextObject)
                break
    '''
    # Debug
    for searchSpaceText in searchSpaceTexts:
        print("START OF BLOCK")
        print(searchSpaceText)
        print("END OF BLOCK")
        input("Wait")
    '''
    return searchSpaceTexts

def main():
    #print(preProcessText(fileText))
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="PHP file to be analyzed")
    parser.add_argument("-c", "--checkNull", type=int, default=1, help="Check if the variables used to store /modify query from result have been initialized or not")
    args = parser.parse_args()

    fileText = readFileContents(args.file)
    if not fileText:
        print("This file is empty!")
        return


    # For Debugging purpose
    #for i in delimitedLines:
    #    print(i)

    # Find variable of interest
    variableOfInterest         = None
    keyPhraseOfInterest        = "->one()"
    delimitedLinesEntireText   = preProcessText(fileText)
    searchSpaceTextObjects = getSearchSpaceText(fileText, keyPhraseOfInterest)

    for searchSpaceTextObject in searchSpaceTextObjects:

        searchSpaceText    = searchSpaceTextObject.searchSpaceText
        delimitedLines     = preProcessText(searchSpaceText)

        for line in delimitedLines:
            # Ignore the lines which don't 
            if line.find(keyPhraseOfInterest) == -1:
                continue

            lvalue = findVariableLHSInLine(line)
            if lvalue:
                variableOfInterest = lvalue

        if not variableOfInterest:
            print("No variable of Interest found")
            return

        ### Find all its daughter variables of variableOfInterest
        # Find lvalue -> rhsVariable map
        #for  
        dependencyMap     = {}
        dependencyObjects = []
        for line in delimitedLines:
            dependencyObject = buildVariableDependenceMap(line)

            # If no { lValue : set(rValue) } is found continue
            if not dependencyObject:
                continue

            lineDependencyMap = dependencyObject.dependencyMap
            dependencyObjects.append(dependencyObject)

            for lhsVariable, rhsVariableSet in lineDependencyMap.items():
                rhsVariableSet_ = dependencyMap.get(lhsVariable, set([]))
                rhsVariableSet_ = rhsVariableSet.union(rhsVariableSet_)
                dependencyMap[lhsVariable] = set(rhsVariableSet_)
                # Reset it
                rhsVariableSet_ = set([])

        # TODO use this if you want to check variable initialization for lot more variables
        #print("DEPENDENCY MAP ", dependencyMap)
        #if isVariableInitialized(variableOfInterest, delimitedLinesEntireText):
        #    print("Variable is already initialized")
        #    return

        fileTextWithNullInitialization = buildInitializationStatements(variableOfInterest, 
                dependencyMap, delimitedLines, delimitedLinesEntireText,
                searchSpaceTextObject, fileText, nullCheck=args.checkNull)
        continuePrompt = input("Continue [Enter] or quit [Q/q]: ")
        if continuePrompt.lower() == "q":
            print("Exiting ...")
            return
        os.system("cls")
        os.system("clear")
        #writeFileContents(args.file, fileTextWithNullInitialization)
    # Write to file
    #print(modifiedCode)


if __name__ == "__main__":
    main()
