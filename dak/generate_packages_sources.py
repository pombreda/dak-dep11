#!/usr/bin/env python

""" Generate Packages/Sources files

@contact: Debian FTPMaster <ftpmaster@debian.org>
@copyright: 2000, 2001, 2002, 2006  James Troup <james@nocrew.org>
@copyright: 2009  Mark Hymers <mhy@debian.org>
@copyright: 2010  Joerg Jaspert <joerg@debian.org>

"""

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

import os
import os.path
import sys
import apt_pkg
from tempfile import mkstemp, mkdtemp
import commands
from multiprocessing import Pool

from daklib import daklog
from daklib.dbconn import *
from daklib.config import Config

################################################################################

Options = None                 #: Commandline arguments parsed into this
Logger = None                  #: Our logging object

################################################################################

def usage (exit_code=0):
    print """Usage: dak generate-packages-sources [OPTIONS]
Generate the Packages/Sources files

  -s, --suite=SUITE(s)       process this suite
                             Default: All suites not marked 'untouchable'
  -f, --force                Allow processing of untouchable suites
                             CAREFUL: Only to be used at point release time!
  -h, --help                 show this help and exit

SUITE can be a space seperated list, e.g.
   --suite=unstable testing
  """

    sys.exit(exit_code)

################################################################################

def generate_packages_sources(arch, suite, tmppath):
    """
    Generate Packages/Sources files with apt-ftparchive for the given suite/arch

    @type suite: string
    @param suite: Suite name

    @type arch: string
    @param arch: Architecture name

    @type tmppath: string
    @param tmppath: The temporary path to work ing
    """

    DAILY_APT_CONF="""
Dir
{
   ArchiveDir "/srv/ftp-master.debian.org/ftp/";
   OverrideDir "/srv/ftp-master.debian.org/scripts/override/";
   CacheDir "/srv/ftp-master.debian.org/database/";
};

Default
{
   Packages::Compress "bzip2 gzip";
   Sources::Compress "bzip2 gzip";
   Contents::Compress "gzip";
   DeLinkLimit 0;
   MaxContentsChange 25000;
   FileMode 0664;
}

TreeDefault
{
   Contents::Header "/srv/ftp-master.debian.org/dak/config/debian/Contents.top";
};

"""

    apt_trees={}
    apt_trees["di"]={}
    apt_trees["testing"]="""
tree "dists/testing"
{
   FakeDI "dists/unstable";
   FileList "/srv/ftp-master.debian.org/database/dists/testing_$(SECTION)_binary-$(ARCH).list";
   SourceFileList "/srv/ftp-master.debian.org/database/dists/testing_$(SECTION)_source.list";
   Sections "main contrib non-free";
   Architectures "%(arch)s";
   BinOverride "override.squeeze.$(SECTION)";
   ExtraOverride "override.squeeze.extra.$(SECTION)";
   SrcOverride "override.squeeze.$(SECTION).src";
};
"""

    apt_trees["squeeze-volatile"]="""
tree "dists/squeeze-volatile"
{
   FileList "/srv/ftp-master.debian.org/database/dists/squeeze-volatile_$(SECTION)_binary-$(ARCH).list";
   SourceFileList "/srv/ftp-master.debian.org/database/dists/squeeze-volatile_$(SECTION)_source.list";
   Sections "main contrib non-free";
   Architectures "%(arch)s";
   BinOverride "override.squeeze.$(SECTION)";
   ExtraOverride "override.squeeze.extra.$(SECTION)";
   SrcOverride "override.squeeze.$(SECTION).src";
   Contents " ";
};
"""

    apt_trees["di"]["testing"]="""
tree "dists/testing/main"
{
   FileList "/srv/ftp-master.debian.org/database/dists/testing_main_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.squeeze.main.$(SECTION)";
   SrcOverride "override.squeeze.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   %(contentsline)s
};

tree "dists/testing/non-free"
{
   FileList "/srv/ftp-master.debian.org/database/dists/testing_non-free_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.squeeze.main.$(SECTION)";
   SrcOverride "override.squeeze.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   %(contentsline)s
};
"""

    apt_trees["unstable"]="""
tree "dists/unstable"
{
   FileList "/srv/ftp-master.debian.org/database/dists/unstable_$(SECTION)_binary-$(ARCH).list";
   SourceFileList "/srv/ftp-master.debian.org/database/dists/unstable_$(SECTION)_source.list";
   Sections "main contrib non-free";
   Architectures "%(arch)s";
   BinOverride "override.sid.$(SECTION)";
   ExtraOverride "override.sid.extra.$(SECTION)";
   SrcOverride "override.sid.$(SECTION).src";
};
"""
    apt_trees["di"]["unstable"]="""
tree "dists/unstable/main"
{
   FileList "/srv/ftp-master.debian.org/database/dists/unstable_main_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.sid.main.$(SECTION)";
   SrcOverride "override.sid.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   %(contentsline)s
};

tree "dists/unstable/non-free"
{
   FileList "/srv/ftp-master.debian.org/database/dists/unstable_non-free_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.sid.main.$(SECTION)";
   SrcOverride "override.sid.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   %(contentsline)s
};
"""

    apt_trees["experimental"]="""
tree "dists/experimental"
{
   FileList "/srv/ftp-master.debian.org/database/dists/experimental_$(SECTION)_binary-$(ARCH).list";
   SourceFileList "/srv/ftp-master.debian.org/database/dists/experimental_$(SECTION)_source.list";
   Sections "main contrib non-free";
   Architectures "%(arch)s";
   BinOverride "override.sid.$(SECTION)";
   SrcOverride "override.sid.$(SECTION).src";
};
"""
    apt_trees["di"]["experimental"]="""
tree "dists/experimental/main"
{
   FileList "/srv/ftp-master.debian.org/database/dists/experimental_main_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.sid.main.$(SECTION)";
   SrcOverride "override.sid.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   %(contentsline)s
};

tree "dists/experimental/non-free"
{
   FileList "/srv/ftp-master.debian.org/database/dists/experimental_non-free_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.sid.main.$(SECTION)";
   SrcOverride "override.sid.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   %(contentsline)s
};
"""

    apt_trees["testing-proposed-updates"]="""
tree "dists/testing-proposed-updates"
{
   FileList "/srv/ftp-master.debian.org/database/dists/testing-proposed-updates_$(SECTION)_binary-$(ARCH).list";
   SourceFileList "/srv/ftp-master.debian.org/database/dists/testing-proposed-updates_$(SECTION)_source.list";
   Sections "main contrib non-free";
   Architectures "%(arch)s";
   BinOverride "override.squeeze.$(SECTION)";
   ExtraOverride "override.squeeze.extra.$(SECTION)";
   SrcOverride "override.squeeze.$(SECTION).src";
   Contents " ";
};
"""
    apt_trees["di"]["testing-proposed-updates"]="""
tree "dists/testing-proposed-updates/main"
{
   FileList "/srv/ftp-master.debian.org/database/dists/testing-proposed-updates_main_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.squeeze.main.$(SECTION)";
   SrcOverride "override.squeeze.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   Contents " ";
};
"""

    apt_trees["proposed-updates"]="""
tree "dists/proposed-updates"
{
   FileList "/srv/ftp-master.debian.org/database/dists/proposed-updates_$(SECTION)_binary-$(ARCH).list";
   SourceFileList "/srv/ftp-master.debian.org/database/dists/proposed-updates_$(SECTION)_source.list";
   Sections "main contrib non-free";
   Architectures "%(arch)s";
   BinOverride "override.lenny.$(SECTION)";
   ExtraOverride "override.lenny.extra.$(SECTION)";
   SrcOverride "override.lenny.$(SECTION).src";
   Contents " ";
};
"""
    apt_trees["di"]["proposed-updates"]="""
tree "dists/proposed-updates/main"
{
   FileList "/srv/ftp-master.debian.org/database/dists/proposed-updates_main_$(SECTION)_binary-$(ARCH).list";
   Sections "debian-installer";
   Architectures "%(arch)s";
   BinOverride "override.lenny.main.$(SECTION)";
   SrcOverride "override.lenny.main.src";
   BinCacheDB "packages-debian-installer-$(ARCH).db";
   Packages::Extensions ".udeb";
   Contents " ";
};
"""

    cnf = Config()
    try:
        # Write apt.conf
        (ac_fd, ac_name) = mkstemp(dir=tmppath, suffix=suite, prefix=arch)
        os.write(ac_fd, DAILY_APT_CONF)
        # here we want to generate the tree entries
        os.write(ac_fd, apt_trees[suite] % {'arch': arch})
        # this special casing needs to go away, but this whole thing may just want an
        # aptconfig class anyways
        if arch != 'source':
            if arch == 'hurd-i386' and suite == 'experimental':
                pass
            elif apt_trees["di"].has_key(suite):
                if arch == "amd64":
                    os.write(ac_fd, apt_trees["di"][suite] %
                             {'arch': arch, 'contentsline': 'Contents "$(DIST)/../Contents-udeb";'})
                else:
                    os.write(ac_fd, apt_trees["di"][suite] % {'arch': arch, 'contentsline': ''})
        os.close(ac_fd)

        print "Going to run apt-ftparchive for %s/%s" % (arch, suite)
        # Run apt-ftparchive generate
        # We dont want to add a -q or -qq here, this output should go into our logs, sometimes
        # it has errormessages we like to see
        os.environ['GZIP'] = '--rsyncable'
        os.chdir(tmppath)
        (result, output) = commands.getstatusoutput('apt-ftparchive generate %s' % os.path.basename(ac_name))
        sn="a-f %s,%s: " % (suite, arch)
        print sn + output.replace('\n', '\n%s' % (sn))

    # Clean up any left behind files
    finally:
        if ac_fd:
            try:
                os.close(ac_fd)
            except OSError:
                pass

        if ac_name:
            try:
                os.unlink(ac_name)
            except OSError:
                pass

def sname(arch):
    return arch.arch_string

########################################################################
########################################################################

def main ():
    global Options, Logger

    cnf = Config()

    for i in ["Help", "Suite", "Force"]:
        if not cnf.has_key("Generate-Packages-Sources::Options::%s" % (i)):
            cnf["Generate-Packages-Sources::Options::%s" % (i)] = ""

    Arguments = [('h',"help","Generate-Packages-Sources::Options::Help"),
                 ('s',"suite","Generate-Packages-Sources::Options::Suite"),
                 ('f',"force","Generate-Packages-Sources::Options::Force")]

    suite_names = apt_pkg.ParseCommandLine(cnf.Cnf, Arguments, sys.argv)
    Options = cnf.SubTree("Generate-Packages-Sources::Options")

    if Options["Help"]:
        usage()

    Logger = daklog.Logger(cnf, 'generate-packages-sources')

    session = DBConn().session()

    if Options["Suite"]:
        # Something here
        suites = []
        for s in suite_names:
            suite = get_suite(s.lower(), session)
            if suite:
                suites.append(suite)
            else:
                print "cannot find suite %s" % s
                Logger.log(['cannot find suite %s' % s])
    else:
        suites=session.query(Suite).filter(Suite.untouchable == False).all()

    startdir = os.getcwd()
    os.chdir(cnf["Dir::TempPath"])

    # For each given suite, each architecture, run one apt-ftparchive
    for s in suites:
        # Setup a multiprocessing Pool. As many workers as we have CPU cores.
        pool = Pool()
        arch_list=get_suite_architectures(s.suite_name, skipsrc=False, skipall=True, session=session)
        Logger.log(['generating output for Suite %s, Architectures %s' % (s.suite_name, map(sname, arch_list))])
        for a in arch_list:
            pool.apply_async(generate_packages_sources, (a.arch_string, s.suite_name, cnf["Dir::TempPath"]))

        # No more work will be added to our pool, close it and then wait for all to finish
        pool.close()
        pool.join()

    os.chdir(startdir)
    # this script doesn't change the database
    session.close()
    Logger.close()

#######################################################################################

if __name__ == '__main__':
    main()