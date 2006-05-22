#!/usr/bin/env python

"""Wrapper to launch dak functionality"""
# Copyright (C) 2005, 2006 Anthony Towns <ajt@debian.org>
# Copyright (C) 2006 James Troup <james@nocrew.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

################################################################################

# well I don't know where you're from but in AMERICA, there's a little
# thing called "abstinent until proven guilty."
#  -- http://harrietmiers.blogspot.com/2005/10/wow-i-feel-loved.html

# (if James had a blog, I bet I could find a funny quote in it to use!)

################################################################################

import sys
import daklib.utils

################################################################################

def init():
    """Setup the list of modules and brief explanation of what they
    do."""

    functionality = [
        ("ls",
         "Show which suites packages are in"),
        ("override",
         "Query/change the overrides"),
        ("check-archive",
         "Archive sanity checks"),
        ("queue-report",
         "Produce a report on NEW and BYHAND packages"),
        
        ("rm",
         "Remove packages from suites"),
        
        ("process-new",
         "Process NEW and BYHAND packages"),
        ("process-unchecked",
         "Process packages in queue/unchecked"),
        ("process-accepted",
         "Install packages into the pool"),
        
        ("make-suite-file-list",
         "Generate lists of packages per suite for apt-ftparchive"),
        ("generate-releases",
         "Generate Release files"),
        ("generate-index-diffs",
         "Generate .diff/Index files"),
        ("clean-suites",
         "Clean unused/superseded packages from the archive"),
        ("clean-queues",
         "Clean cruft from incoming"),
        ("clean-proposed-updates",
         "Remove obsolete .changes from proposed-updates"),
        
        ("check-overrides",
         "Override cruft checks"),
        ("check-proposed-updates",
         "Dependency checking for proposed-updates"),
        ("compare-suites",
         "Show fixable discrepencies between suites"),
        ("control-overrides",
         "Manipulate/list override entries in bulk"),
        ("control-suite",
         "Manipulate suites in bulk"),
        ("cruft-report",
         "Check for obsolete or duplicated packages"),
        ("decode-dot-dak",
         "Display contents of a .dak file"),
        ("examine-package",
         "Show information useful for NEW processing"),
        ("find-null-maintainers",
         "Check for users with no packages in the archive"),
        ("import-archive",
         "Populate SQL database based from an archive tree"),
        ("import-ldap-fingerprints",
         "Syncs fingerprint and uid tables with Debian LDAP db"),
        ("import-users-from-passwd",
         "Sync PostgreSQL users with passwd file"),
        ("init-db",
         "Update the database to match the conf file"),
        ("init-dirs",
         "Initial setup of the archive"),
        ("make-maintainers",
         "Generates Maintainers file for BTS etc"),
        ("make-overrides",
         "Generates override files"),
        ("mirror-split",
         "Split the pool/ by architecture groups"),
        ("poolize",
         "Move packages from dists/ to pool/"),
        ("reject-proposed-updates",
         "Manually reject from proposed-updates"),
        ("security-install",
         "Install a security upload into the archive"),
        ("split-done",
         "Split queue/done into a date-based hierarchy"),
        ("stats",
         "Generate statistics"),
        ("symlink-dists",
         "Generate compatability symlinks from dists/ into pool/"),
        ]
    return functionality
    
################################################################################

def usage(functionality, exit_code=0):
    """Print a usage message and exit with 'exit_code'."""

    print """Usage: dak COMMAND [...]
Run DAK commands.  (Will also work if invoked as COMMAND.)

Availble commands:"""
    for (command, description) in functionality:
        print "  %-23s %s" % (command, description)
    sys.exit(exit_code)

################################################################################

def main():
    """Launch dak functionality."""

    functionality = init()
    modules = [ command for (command, _) in functionality ]
    
    if len(sys.argv) == 0:
        daklib.utils.fubar("err, argc == 0? how is that possible?")
    elif (len(sys.argv) == 1
          or (len(sys.argv) == 2 and
              (sys.argv[1] == "--help" or sys.argv[1] == "-h"))):
        usage(functionality)

    # First see if we were invoked with/as the name of a module
    cmdname = sys.argv[0]
    cmdname = cmdname[cmdname.rfind("/")+1:]
    if cmdname in modules:
        pass
    # Otherwise the argument is the module
    else:
        cmdname = sys.argv[1]
        sys.argv = [sys.argv[0] + " " + sys.argv[1]] + sys.argv[2:]
        if cmdname not in modules:
            match = []
            for name in modules:
                if name.startswith(cmdname):
                    match.append(name)
            if len(match) == 1:
                cmdname = match[0]
            elif len(match) > 1:
                daklib.utils.warn("ambiguous command '%s' - could be %s" \
                           % (cmdname, ", ".join(match)))
                usage(functionality, 1)
            else:
                daklib.utils.warn("unknown command '%s'" % (cmdname))
                usage(functionality, 1)

    # Invoke the module
    module = __import__(cmdname.replace("-","_"))
    module.main()

################################################################################

if __name__ == "__main__":
    main()