import gspread
import sys, os
import traceback
from inspect import getsourcefile
from os.path import abspath

directory = abspath(getsourcefile(lambda: 0))
#check if system uses forward or backslashes for writing directories
if (directory.rfind("/") != -1):
  newDirectory = directory[:(directory.rfind("/") + 1)]
else:
  newDirectory = directory[:(directory.rfind("\\") + 1)]
os.chdir(newDirectory)


def get_queue():
  try:
    gc = gspread.service_account(filename="googleKey.json")
    sh = gc.open_by_url(
      """https://docs.google.com/spreadsheets/d/1j-Ny43mj9cY_Im4N9mOrLfIYpDTK-4Jk90OKdcASgfA/edit?usp=sharing"""
    )
    worksheets = sh.worksheets()
    format = ""
    for ws in worksheets:
      if ws.title != "Example Format":
        game = ws.title
        current_host = ws.acell("B2").value
        format = format + "\n**{}**\n\nCurrent: {}\n\n".format(
          game, current_host)
        for i in range(3, 20):
          time = ws.cell(i, 1).value
          hosts = ws.cell(i, 2).value
          if (time is None):
            break
          format = format + "-{}: {}\n".format(time, hosts)

    return (format)
  except:
    #traceback.print_exc()
    return (
      "Google API rate limit exceeded, or API credential fail. Wait a few minutes before updating."
    )
