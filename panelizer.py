#!/usr/bin/env python3

import os
import sys
from argparse import ArgumentParser
from pathlib import Path
import pcbnew
from pcbnew import *

"""
A simple script to create a v-scored panel of a KiCad board.
Original author: Willem Hillier
"""

# set up command-line arguments parser
parser = ArgumentParser(description="A script to panelize KiCad files.")
parser.add_argument(dest="sourceBoardFile", help='Path to the *.kicad_pcb file to be panelized')
parser.add_argument('--numx', type=int, help='Number of boards in X direction')
parser.add_argument('--numy', type=int, help='Number of boards in Y direction')
parser.add_argument('--panelx', type=int, help='Maximum panel size in X direction')
parser.add_argument('--panely', type=int, help='Maximum panel size in Y direction')
parser.add_argument('--hrail', type=int, default=0, help='Horizontal edge rail width')
parser.add_argument('--vrail', type=int, default=0, help='Vertical edge rail width')
parser.add_argument('--hrailtext', help='Text to put on the horizontal edge rail')
parser.add_argument('--vrailtext', help='Text to put on the vertical edge rail')
args = parser.parse_args()
sourceBoardFile = args.sourceBoardFile
NUM_X = args.numx
NUM_Y = args.numy
PANEL_X = args.panelx
PANEL_Y = args.panely
HORIZONTAL_EDGE_RAIL_WIDTH = args.hrail
VERTICAL_EDGE_RAIL_WIDTH = args.vrail
HORIZONTAL_EDGE_RAIL_TEXT = args.hrailtext
VERTICAL_EDGE_RAIL_TEXT = args.vrailtext

# check that input board is a *.kicad_pcb file
sourceFileExtension = os.path.splitext(sourceBoardFile)[1]
if not(sourceFileExtension == '.kicad_pcb'):
    print(sourceBoardFile + " is not a *.kicad_pcb file. Quitting.")
    quit()

# check that railtext is at least 1mm
if (HORIZONTAL_EDGE_RAIL_TEXT and HORIZONTAL_EDGE_RAIL_WIDTH < 2) or (VERTICAL_EDGE_RAIL_TEXT and VERTICAL_EDGE_RAIL_WIDTH < 2):
    print("Rail width must be at least 2mm if using rail text. Quitting.")
    quit()

# only allow numbers or panels
if (PANEL_X or PANEL_Y) and (NUM_X or NUM_Y):
    print("Specify number of boards or size of panel, not both. Quitting.")
    quit()

# expect panel size or number of boards
if (not PANEL_X or not PANEL_Y) and (not NUM_X or not NUM_Y):
    print("Specify number of boards or size of panel. Quitting.")
    quit()

# warn if user has specified both rails
if (HORIZONTAL_EDGE_RAIL_WIDTH and VERTICAL_EDGE_RAIL_WIDTH):
    print("Warning: do you really want both edge rails?")

# output file name is format {inputFile}_panelized.kicad_pcb
panelOutputFile = os.path.splitext(sourceBoardFile)[0] + "_panelized.kicad_pcb"

# all dimension parameters used by this script are mm unless otherwise noted
SCALE = 1000000

# v-scoring parameters
V_SCORE_LAYER = "Edge.Cuts"
V_SCORE_LINE_LENGTH_BEYOND_BOARD = -0.05
V_SCORE_TEXT_CENTER_TO_LINE_LENGTH = 10
V_SCORE_TEXT = "V-SCORE"
V_SCORE_TEXT_SIZE = 2
V_SCORE_TEXT_THICKNESS = 0.1
V_SCORE_TEXT_LAYER = "Cmts.User"

# creates a list that can be used to lookup layer numbers by their name
def get_layertable():
    layertable = {}
    numlayers = pcbnew.PCB_LAYER_ID_COUNT
    for i in range(numlayers):
        layertable[board.GetLayerName(i)] = i
    return layertable

# load source board
board = LoadBoard(sourceBoardFile)

# set up layer table
layertable = get_layertable()

# get dimensions of board
boardWidth = board.GetBoardEdgesBoundingBox().GetWidth()
boardHeight = board.GetBoardEdgesBoundingBox().GetHeight()

# how many whole boards can we fit on the panel
if (PANEL_X):
    NUM_X = int( (PANEL_X*SCALE - 2*HORIZONTAL_EDGE_RAIL_WIDTH*SCALE) / boardWidth )

if (PANEL_Y):
    NUM_Y = int( (PANEL_Y*SCALE - 2*VERTICAL_EDGE_RAIL_WIDTH*SCALE) / boardHeight )

# check we can actually panelize the board
if (NUM_X == 0 or NUM_Y == 0):
    print("Panel size is too small for board. Quitting.")
    quit()

# array of tracks
tracks = board.GetTracks()
newTracks = []
for sourceTrack in tracks:                          # iterate through each track to be copied
    for x in range(0,NUM_X):                        # iterate through x direction
        for y in range(0, NUM_Y):                   # iterate through y direction
            if((x!=0)or(y!=0)):                     # do not duplicate source object to location
                newTrack = sourceTrack.Duplicate()
                newTrack.Move(wxPoint(x*boardWidth, y*boardHeight)) # move to correct location
                newTracks.append(newTrack)          # add to temporary list of tracks

for track in newTracks:
    tracks.Append(track)

# array of drawing objects
drawings = board.GetDrawings()
newDrawings = []
for drawing in drawings:
    for x in range(0,NUM_X):
        for y in range(0, NUM_Y):
            if((x!=0)or(y!=0)):
                newDrawing = drawing.Duplicate()
                newDrawing.Move(wxPoint(x*boardWidth, y*boardHeight))
                newDrawings.append(newDrawing)

for drawing in newDrawings:
    board.Add(drawing)

# array of modules
modules = board.GetModules()
newModules = []
for sourceModule in modules:
    for x in range(0,NUM_X):
        for y in range(0, NUM_Y):
            if((x!=0)or(y!=0)):
                newModule = pcbnew.MODULE(sourceModule)
                newModule.SetPosition(wxPoint(x*boardWidth + sourceModule.GetPosition().x, y*boardHeight + sourceModule.GetPosition().y))
                newModules.append(newModule)

for module in newModules:
    board.Add(module)

# array of zones
modules = board.GetModules()
newZones = []
for a in range(0,board.GetAreaCount()):
    sourceZone = board.GetArea(a)
    for x in range(0,NUM_X):
        for y in range(0, NUM_Y):
            if((x!=0)or(y!=0)):
                newZone = sourceZone.Duplicate()
                newZone.SetNet(sourceZone.GetNet())
                newZone.Move(wxPoint(x*boardWidth, y*boardHeight))
                newZones.append(newZone)

for zone in newZones:
    board.Add(zone)

# get dimensions and center coordinate of entire array (without siderails to be added shortly)
arrayWidth = board.GetBoardEdgesBoundingBox().GetWidth()
arrayHeight = board.GetBoardEdgesBoundingBox().GetHeight()
arrayCenter = board.GetBoardEdgesBoundingBox().GetCenter()

# erase all existing edgeCuts objects (individual board outlines)
drawings = board.GetDrawings()
for drawing in drawings:
    if(drawing.IsOnLayer(layertable["Edge.Cuts"])):
        drawing.DeleteStructure()

# top Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart(pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd(pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# right Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart(pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd(pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# bottom Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart(pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd(pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# left Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart(pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd(pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# re-calculate board dimensions with new edge cuts
panelWidth = board.GetBoardEdgesBoundingBox().GetWidth()
panelHeight = board.GetBoardEdgesBoundingBox().GetHeight()
panelCenter = arrayCenter # should be the same as arrayCenter

# absolute edges of v-scoring
vscore_top = panelCenter.y - panelHeight/2 - V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
vscore_bottom = panelCenter.y + panelHeight/2 + V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
vscore_right = panelCenter.x + panelWidth/2 + V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
vscore_left = panelCenter.x - panelWidth/2 - V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
v_scores = []

# vertical v-scores
if HORIZONTAL_EDGE_RAIL_WIDTH >0:
    rangeStart = 0
    rangeEnd = NUM_X+1
else:
    rangeStart = 1
    rangeEnd = NUM_X

for x in range(rangeStart, rangeEnd):
    x_loc = panelCenter.x - panelWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE + boardWidth*x
    v_score_line = pcbnew.DRAWSEGMENT(board)
    v_scores.append(v_score_line)
    v_score_line.SetStart(pcbnew.wxPoint(x_loc, vscore_top))
    v_score_line.SetEnd(pcbnew.wxPoint(x_loc, vscore_bottom))
    v_score_line.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text = pcbnew.TEXTE_PCB(board)
    v_score_text.SetText(V_SCORE_TEXT)
    v_score_text.SetPosition(wxPoint(x_loc, vscore_top - V_SCORE_TEXT_CENTER_TO_LINE_LENGTH*SCALE))
    v_score_text.SetTextSize(pcbnew.wxSize(SCALE*V_SCORE_TEXT_SIZE,SCALE*V_SCORE_TEXT_SIZE))
    v_score_text.SetLayer(layertable[V_SCORE_TEXT_LAYER])
    v_score_text.SetTextAngle(900)
    board.Add(v_score_text)

# horizontal v-scores
if VERTICAL_EDGE_RAIL_WIDTH >0:
    rangeStart = 0
    rangeEnd = NUM_Y+1
else:
    rangeStart = 1
    rangeEnd = NUM_Y

for y in range(rangeStart, rangeEnd):
    y_loc = panelCenter.y - panelHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE + boardHeight*y
    v_score_line = pcbnew.DRAWSEGMENT(board)
    v_scores.append(v_score_line)
    v_score_line.SetStart(pcbnew.wxPoint(vscore_left, y_loc))
    v_score_line.SetEnd(pcbnew.wxPoint(vscore_right, y_loc))
    v_score_line.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text = pcbnew.TEXTE_PCB(board)
    v_score_text.SetText(V_SCORE_TEXT)
    v_score_text.SetPosition(wxPoint(vscore_left - V_SCORE_TEXT_CENTER_TO_LINE_LENGTH*SCALE, y_loc))
    v_score_text.SetTextSize(pcbnew.wxSize(SCALE*V_SCORE_TEXT_SIZE,SCALE*V_SCORE_TEXT_SIZE))
    v_score_text.SetLayer(layertable[V_SCORE_TEXT_LAYER])
    v_score_text.SetTextAngle(0)
    board.Add(v_score_text)

# move vscores to edge.cuts layer
for vscore in v_scores:
    vscore.SetLayer(layertable["Edge.Cuts"])
    board.Add(vscore)

# move back to correct layer
for vscore in v_scores:
    vscore.SetLayer(layertable[V_SCORE_LAYER])

# add text to rail
if args.hrailtext:
    hrail_text = pcbnew.TEXTE_PCB(board)
    hrail_text.SetText(HORIZONTAL_EDGE_RAIL_TEXT)
    hrail_text.SetTextSize(pcbnew.wxSize(SCALE*1,SCALE*1))
    hrail_text.SetLayer(F_SilkS)
    hrail_text.SetHorizJustify(GR_TEXT_HJUSTIFY_LEFT)
    hrail_text.SetPosition(wxPoint(panelCenter.x - panelWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH/2*SCALE, panelCenter.y + panelHeight/2 - SCALE*1))
    hrail_text.SetTextAngle(900) # rotate if on hrail
    board.Add(hrail_text)

if args.vrailtext:
    vrail_text = pcbnew.TEXTE_PCB(board)
    vrail_text.SetText(VERTICAL_EDGE_RAIL_TEXT)
    vrail_text.SetTextSize(pcbnew.wxSize(SCALE*1,SCALE*1))
    vrail_text.SetLayer(F_SilkS)
    vrail_text.SetHorizJustify(GR_TEXT_HJUSTIFY_LEFT)
    vrail_text.SetPosition(wxPoint(panelCenter.x - panelWidth/2 + SCALE*1, panelCenter.y - panelHeight/2 + VERTICAL_EDGE_RAIL_WIDTH/2*SCALE))
    board.Add(vrail_text)

# save output
board.Save(panelOutputFile)

# print report
if (PANEL_X or PANEL_Y):
    print("You can fit " + str(NUM_X) +" x " + str(NUM_Y) + " boards on the panel")
print("Board dimensions: " + str(boardWidth/SCALE) + "x" + str(boardHeight/SCALE) + "mm")
print("Panel dimensions: " + str(panelWidth/SCALE) + "x" + str(panelHeight/SCALE) + "mm")
