#!/usr/bin/env python

# Various statistical pr0nography fun and games
# Copyright (C) 2000, 2001, 2002, 2003, 2006  James Troup <james@nocrew.org>

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

# <aj>    can we change the standards instead?
# <neuro> standards?
# <aj>    whatever we're not conforming to
# <aj>    if there's no written standard, why don't we declare linux as
#         the defacto standard
# <aj>    go us!

# [aj's attempt to avoid ABI changes for released architecture(s)]

################################################################################

import pg, sys
import apt_pkg
import daklib.utils

################################################################################

Cnf = None
projectB = None

################################################################################

def usage(exit_code=0):
    print """Usage: dak stats MODE
Print various stats.

  -h, --help                show this help and exit.

The following MODEs are available:

  arch-space    - displays space used by each architecture
  pkg-nums      - displays the number of packages by suite/architecture
  daily-install - displays daily install stats suitable for graphing
"""
    sys.exit(exit_code)

################################################################################

def per_arch_space_use():
    q = projectB.query("""
SELECT a.arch_string as Architecture, sum(f.size)
  FROM files f, binaries b, architecture a
  WHERE a.id=b.architecture AND f.id=b.file
  GROUP BY a.arch_string""")
    print q
    q = projectB.query("SELECT sum(size) FROM files WHERE filename ~ '.(diff.gz|tar.gz|dsc)$'")
    print q

################################################################################

def daily_install_stats():
    stats = {}
    file = daklib.utils.open_file("2001-11")
    for line in file.readlines():
        split = line.strip().split('~')
        program = split[1]
        if program != "katie" and program != "process-accepted":
            continue
        action = split[2]
        if action != "installing changes" and action != "installed":
            continue
        date = split[0][:8]
        if not stats.has_key(date):
            stats[date] = {}
            stats[date]["packages"] = 0
            stats[date]["size"] = 0.0
        if action == "installing changes":
            stats[date]["packages"] += 1
        elif action == "installed":
            stats[date]["size"] += float(split[5])

    dates = stats.keys()
    dates.sort()
    for date in dates:
        packages = stats[date]["packages"]
        size = int(stats[date]["size"] / 1024.0 / 1024.0)
        print "%s %s %s" % (date, packages, size)

################################################################################

def longest(list):
    longest = 0
    for i in list:
        l = len(i)
        if l > longest:
            longest = l
    return longest

def suite_sort(a, b):
    if Cnf.has_key("Suite::%s::Priority" % (a)):
        a_priority = int(Cnf["Suite::%s::Priority" % (a)])
    else:
        a_priority = 0
    if Cnf.has_key("Suite::%s::Priority" % (b)):
        b_priority = int(Cnf["Suite::%s::Priority" % (b)])
    else:
        b_priority = 0
    return cmp(a_priority, b_priority)

def output_format(suite):
    output_suite = []
    for word in suite.split("-"):
        output_suite.append(word[0])
    return "-".join(output_suite)

# Obvious query with GROUP BY and mapped names                  -> 50 seconds
# GROUP BY but ids instead of suite/architecture names          -> 28 seconds
# Simple query                                                  -> 14 seconds
# Simple query into large dictionary + processing               -> 21 seconds
# Simple query into large pre-created dictionary + processing   -> 18 seconds

def number_of_packages():
    arches = {}
    arch_ids = {}
    suites = {}
    suite_ids = {}
    d = {}
    # Build up suite mapping
    q = projectB.query("SELECT id, suite_name FROM suite")
    suite_ql = q.getresult()
    for i in suite_ql:
        (id, name) = i
        suites[id] = name
        suite_ids[name] = id
    # Build up architecture mapping
    q = projectB.query("SELECT id, arch_string FROM architecture")
    for i in q.getresult():
        (id, name) = i
        arches[id] = name
        arch_ids[name] = id
    # Pre-create the dictionary
    for suite_id in suites.keys():
        d[suite_id] = {}
        for arch_id in arches.keys():
            d[suite_id][arch_id] = 0
    # Get the raw data for binaries
    q = projectB.query("""
SELECT ba.suite, b.architecture
  FROM binaries b, bin_associations ba
 WHERE b.id = ba.bin""")
    # Simultate 'GROUP by suite, architecture' with a dictionary
    for i in q.getresult():
        (suite_id, arch_id) = i
        d[suite_id][arch_id] = d[suite_id][arch_id] + 1
    # Get the raw data for source
    arch_id = arch_ids["source"]
    q = projectB.query("""
SELECT suite, count(suite) FROM src_associations GROUP BY suite;""")
    for i in q.getresult():
        (suite_id, count) = i
        d[suite_id][arch_id] = d[suite_id][arch_id] + count
    ## Print the results
    # Setup
    suite_list = suites.values()
    suite_list.sort(suite_sort)
    suite_id_list = []
    suite_arches = {}
    for suite in suite_list:
        suite_id = suite_ids[suite]
        suite_arches[suite_id] = {}
        for arch in Cnf.ValueList("Suite::%s::Architectures" % (suite)):
            suite_arches[suite_id][arch] = ""
        suite_id_list.append(suite_id)
    output_list = [ output_format(i) for i in suite_list ]
    longest_suite = longest(output_list)
    arch_list = arches.values()
    arch_list.sort()
    longest_arch = longest(arch_list)
    # Header
    output = (" "*longest_arch) + " |"
    for suite in output_list:
        output = output + suite.center(longest_suite)+" |"
    output = output + "\n"+(len(output)*"-")+"\n"
    # per-arch data
    arch_list = arches.values()
    arch_list.sort()
    longest_arch = longest(arch_list)
    for arch in arch_list:
        arch_id = arch_ids[arch]
        output = output + arch.center(longest_arch)+" |"
        for suite_id in suite_id_list:
            if suite_arches[suite_id].has_key(arch):
                count = repr(d[suite_id][arch_id])
            else:
                count = "-"
            output = output + count.rjust(longest_suite)+" |"
        output = output + "\n"
    print output

################################################################################

def main ():
    global Cnf, projectB

    Cnf = daklib.utils.get_conf()
    Arguments = [('h',"help","Stats::Options::Help")]
    for i in [ "help" ]:
	if not Cnf.has_key("Stats::Options::%s" % (i)):
	    Cnf["Stats::Options::%s" % (i)] = ""

    args = apt_pkg.ParseCommandLine(Cnf, Arguments, sys.argv)

    Options = Cnf.SubTree("Stats::Options")
    if Options["Help"]:
	usage()

    if len(args) < 1:
        daklib.utils.warn("dak stats requires a MODE argument")
        usage(1)
    elif len(args) > 1:
        daklib.utils.warn("dak stats accepts only one MODE argument")
        usage(1)
    mode = args[0].lower()

    projectB = pg.connect(Cnf["DB::Name"], Cnf["DB::Host"], int(Cnf["DB::Port"]))

    if mode == "arch-space":
        per_arch_space_use()
    elif mode == "pkg-nums":
        number_of_packages()
    elif mode == "daily-install":
        daily_install_stats()
    else:
        daklib.utils.warn("unknown mode '%s'" % (mode))
        usage(1)

################################################################################

if __name__ == '__main__':
    main()
