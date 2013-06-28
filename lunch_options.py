from optparse import OptionParser

usage = "usage: %prog [options]"
optionParser = OptionParser(usage = usage)
optionParser.add_option("-v", "--verbose",
                  action = "store_true", dest = "verbose", default = False,
                  help = "Enable verbose output")
optionParser.add_option("--autoUpdate",
                  default = True, dest = "noUpdates", action = "store_false",
                  help = "Automatically pull updates from Git.")