#!/usr/bin/python3

import argparse
import re

########## UTILITY CLASS ##############
def readFileContents(qualifiedFilename):
    """
    Read file contents and apply
    """
    return open(qualifiedFilename).read()

#######################################
class DependencyObject:
    def __init__(self, dependencyMap, line, lValue):
        self.dependencyMap = dependencyMap
        self.line          = line
        self.lValue        = lValue

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


def buildInitializationStatements(variableOfInterest, dependencyMap, delimitedLines, fileText):
    """
    """
    
    rValuesSet = dependencyMap.get(variableOfInterest, [])
    if not rValuesSet:
        print("OOPS variableOfInterest not found in dependencyMap")
        return

    # CASE 1 parent initialization | parent null check
    daughterVariables = findDaughterVariables(variableOfInterest, dependencyMap)

    placeNullInitialization(variableOfInterest, daughterVariables, delimitedLines, fileText)



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
    """
    # If the lValue exists
    for line in delimitedLines:
        if (line.find("null") != -1) and (line.find(lValue) != -1):
            print("Initialized here ", line)
            return True

    return False

def generateNullInitialized(lValue):
    """
    For lValue initialize it
    """
    return "\n    %s = null; //NOTE Auto-generated initialization"%lValue


def placeNullInitialization(lValue, daughterVariables, delimitedLines, fileText):
    """
    places null initialization statement before the first instance of the lvalue
    """
    firstInstanceLine = 0
    initializationStatement = generateNullInitialized(lValue)
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

    # Append last line without colon
    fileTextWithNullInitialization += delimitedLinesWithoutPreprocessing[-1]
    
    # For daughterVariables
    daughterLinesToBeRemoved = [] # These are also the lines which will be inside null check
    nullCheckBlock = "\n\t\\\\NOTE Auto-generated if Block\n    if (%s){\n%s    }"%(lValue, "      %s\n"*len(daughterVariables))
    for daughterVariable in daughterVariables:
        for line in delimitedLines:
            if line.find(daughterVariable) != -1:
                daughterLinesToBeRemoved.append(line.strip())
                break

    print(daughterLinesToBeRemoved)
    nullCheckBlock = nullCheckBlock % tuple(daughterLinesToBeRemoved)
    # Prepare null check block
    print(nullCheckBlock)

    nullCheckBlockInsertionPlace = fileTextWithNullInitialization.find(
                                        daughterLinesToBeRemoved[0])
    for daughterLineToBeRemoved in daughterLinesToBeRemoved:
        fileTextWithNullInitialization = fileTextWithNullInitialization.replace(daughterLineToBeRemoved, "")

    fileTextWithNullInitialization = fileTextWithNullInitialization[:nullCheckBlockInsertionPlace] \
                                      + "\n " + nullCheckBlock \
                                      + fileTextWithNullInitialization[nullCheckBlockInsertionPlace:]

    print("FINAL \n", fileTextWithNullInitialization)
    return fileTextWithNullInitialization

def main():
    #print(preProcessText(fileText))
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="PHP file to be analyzed")
    args = parser.parse_args()

    fileText = readFileContents(args.file)
    if not fileText:
        print("This file is empty!")
        return

    delimitedLines     = preProcessText(fileText)

    for i in delimitedLines:
        print(i)

    # Find variable of interest
    variableOfInterest  = None
    keyPhraseOfInterest = "->one()"
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

    # See if it is initialized with null
    if isVariableInitialized(variableOfInterest, delimitedLines):
        print("Variable is already initialized")
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

    print("---------")
    print("Final Dependency Map", dependencyMap)

    # Generate null initialization code
    #modifiedCode = placeNullInitialization(variableOfInterest, delimitedLines, fileText)
    buildInitializationStatements(variableOfInterest, dependencyMap, delimitedLines,
                           fileText)
    #print(modifiedCode)


if __name__ == "__main__":
    main()
