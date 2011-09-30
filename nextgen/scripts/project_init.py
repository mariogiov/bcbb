# -*- coding: utf-8 -*-
"""
    pavement_init.py
    ~~~~~~~~~~~~~~~~

    Setup pavement configuration file for a project for use with 
    paver (http://paver.github.com/paver/).

"""

import sys
import os
import time
from os import path
from termcolor import colored, cprint
from mako.template import Template

TERM_ENCODING = getattr(sys.stdin, 'encoding', None)

PROMPT_PREFIX = '> '

SBATCH_TEMPLATE = '''\
#!/bin/bash -l
TMPDIR=/scratch/$SLURM_JOB_ID

#SBATCH -A ${project_id}
#SBATCH -t ${time}
#SBATCH -o ${jobname}.stdout
#SBATCH -e ${jobname}.stderr
#SBATCH -J ${jobname}
#SBATCH -D ${workdir}
#SBATCH -p ${partition}
#SBATCH -n ${cores}
#SBATCH --mail-type=${mail_type}
#SBATCH --mail-user=${mail_user}
<%
if (constraint):
    constraint_str = "#SBATCH -C " + constraint
else:
    constraint_str = ""
%>
${constraint_str}
module load biopython
module load bioinfo-tools
module unload R
module load R/2.13.0
${header}
${command_str}
${footer}
'''

PROJ_CONF_YAML = Template('''\
galaxy_config:
third_party:
  top_dir: ${top_dir}
  log_dir: ${log_dir}
  intermediate_dir: ${intermediate_dir}
  genome_build: hg19
program:
  bowtie: bowtie
  samtools: samtools
  bwa: bwa
  ucsc_bigwig: wigToBigWig
  picard: /bubo/sw/apps/bioinfo/picard/1.41
  gatk: /bubo/sw/apps/bioinfo/GATK/1.0.5909
  snpEff: 
  fastqc: fastqc
  pdflatex: pdflatex
  barcode: barcode_sort_trim.py
algorithm:
  aligner: bwa
  max_errors: 2
  num_cores: 8
  platform: illumina
  recalibrate: true
  snpcall: true
  dbsnp: 
  bc_mismatch: 2
  bc_read: 1
  bc_position: 3
  java_memory: 3g
  save_diskspace: true

analysis:
  towig_script: bam_to_wiggle.py
distributed:
  rabbitmq_vhost: bionextgen
# configuration algorithm changes for custom post-processing steps
custom_algorithms:
  'SNP calling':
    aligner: bwa
    recalibrate: true
    snpcall: true
    dbsnp:
  'Minimal':
    aligner: ""
''')

PAVEMENT_FILE = Template('''\
"""
${project} pavement file

Created by pavement_init.py on ${now}.
"""
# This is a pavement configuration file generated by pavement_init.py.
# Some configurations have been commented out, but are included to show
# additional configurations and imports
import os
import itertools
import sys
import logbook
import glob
log = logbook.Logger("paver")

from mako.template import Template
from paver.easy import *
from bcbio.paver.misc import *
from bcbio.paver.project import *
import paver.doctools

handler = logbook.FileHandler(os.path.join("${log_dir}", "%s.log" % log.name))
handler.push_application()

options(
    log = log,
    dirs = Bunch(
        top = "${top_dir}",
        sbatch = "${sbatch_dir}",
        log = "${log_dir}",
        git = "${git_dir}",
        intermediate = "${intermediate_dir}",
        data = os.path.join("${top_dir}", "data"),
        ),
    sbatch = Bunch(
        project_id = "${uppmax_project_id}",
        constraint = '',
        time = '50:00:00',
        jobname = '',
        workdir = "${intermediate_dir}",
        partition = 'node',
        cores = '8',
        mail_type = 'ALL',
        mail_user = "${mail_user}",
        header = '',
        footer = '',
        command_str = '',
        ),
    mako = Bunch(
        sbatch = Template(filename = "sbatch_template.mako"),
        ),
    sphinx = Bunch(
        docroot = "${sphinx_dir}",
        ),
    # useful option for facilitating rsync
    #rsync = Bunch(
    #    host = "",
    #    user = "",
    #    src = "",
    #    dest = "",
    #    ),
    )
# Find flowcell ids
options(
    illumina = Bunch(
        flowcell_ids = os.listdir(options.dirs.data),
        ),
    )
# ##############################
# # Sbatch tasks
# # Note: these tasks do not actually run sbatch, they
# # just generate the sbatch files
# ##############################


# ##############################
# # Sphinx related tasks
# ##############################

'''
)

## Shamelessly stolen from sphinx-quickstart
def mkdir_p(dir):
    if path.isdir(dir):
        return
    os.makedirs(dir)

class ValidationError(Exception):
    """Raised for validation errors."""

def is_path(x):
    if path.exists(x) and not path.isdir(x):
        raise ValidationError("Please enter a valid path name.")
    return x

def nonempty(x):
    if not x:
        raise ValidationError("Please enter some text.")
    return x

def choice(*l):
    def val(x):
        if x not in l:
            raise ValidationError('Please enter one of %s.' % ', '.join(l))
        return x
    return val

def boolean(x):
    if x.upper() not in ('Y', 'YES', 'N', 'NO'):
        raise ValidationError("Please enter either 'y' or 'n'.")
    return x.upper() in ('Y', 'YES')

def suffix(x):
    if not (x[0:1] == '.' and len(x) > 1):
        raise ValidationError("Please enter a file suffix, "
                              "e.g. '.rst' or '.txt'.")
    return x

def ok(x):
    return x


def do_prompt(d, key, text, default=None, validator=nonempty):
    while True:
        if default:
            prompt = PROMPT_PREFIX + '%s [%s]: ' % (text, default)
        else:
            prompt = PROMPT_PREFIX + text + ': '
        x = raw_input(prompt)
        if default and not x:
            x = default
        if x.decode('ascii', 'replace').encode('ascii', 'replace') != x:
            if TERM_ENCODING:
                x = x.decode(TERM_ENCODING)
            else:
                print '''* Note: non-ASCII characters entered 
and terminal encoding unknown -- assuming
UTF-8 or Latin-1.'''
                try:
                    x = x.decode('utf-8')
                except UnicodeDecodeError:
                    x = x.decode('latin1')
        try:
            x = validator(x)
        except ValidationError, err:
            print '* ' + str(err)
            continue
        break
    d[key] = x

def inner_main(args):
    d = {}
    print colored('''pavement_init.py configuration''', attrs=["bold"])
    print

    print '''
The project name is usually of the form j_doe_00_00, but can be any name. This name will be used to generate a directory where the pavement.py file is installed
'''
    do_prompt(d, 'project', 'Project name')

    print '''
The top path defines the root of the project. Relative to this path there should be a data directory with raw data, an intermediate directory with intermediate data analyses. pavement_init.py will set up a directory for the pavement.py file, an sbatch directory for sbatch files, and a log directory for logging.
'''
    do_prompt(d, 'top_dir', 'top path for the project', '.', is_path)
    d['top_dir'] = path.abspath(d['top_dir'])
    d['git_dir'] = path.join(d['top_dir'], d['project'] + '_git')
    while path.isfile(path.join(d['git_dir'], 'pavement.py')):
        print
        print colored('Error: an existing pavement.py has been found in the selected project top directory path.', attrs=["bold"])
        print 'will not overwrite existing pavement.py files.'
        print
        do_prompt(d, 'top_dir', 'Please enter a new top path (or just Enter '
                  'to exit)', '', is_path)
        if not d['top_dir']:
            sys.exit(1)

    do_prompt(d, 'uppmax_project_id', 'which uppmax project id is this project related to? used in the template sbatch file')
    do_prompt(d, 'mail_user', 'what is your mail address?')

    ## Set remaining dictionary variables
    d['now'] = time.asctime()
    d['sbatch_dir'] = path.join(d['top_dir'], 'sbatch')
    d['log_dir'] = path.join(d['top_dir'], 'log')
    d['sphinx_dir'] = path.join(d['git_dir'], 'doc')
    d['intermediate_dir'] = path.join(d['top_dir'], "intermediate", "nobackup")

    mkdir_p(d['git_dir'])
    mkdir_p(d['sbatch_dir'])
    mkdir_p(d['log_dir'])
    mkdir_p(d['sphinx_dir'])
    pavement_text = PAVEMENT_FILE.render(**d)
    f = open(path.join(d['git_dir'], 'pavement.py'), 'w')
    f.write(PAVEMENT_FILE.render(**d))
    f.close()
    f = open(path.join(d['git_dir'], 'sbatch_template.mako'), 'w')
    f.write(SBATCH_TEMPLATE)
    f.close()
    f = open(path.join(d['git_dir'], 'proj_conf.yaml'), 'w')
    f.write(PROJ_CONF_YAML.render(**d))
    f.close()

    print "Done setting up the paver project. Please run 'sphinx-quickstart' in %s if you haven't done so yet" % (d['sphinx_dir'])


def main(argv=sys.argv):
    print "Started main"
    try:
        return inner_main(argv)
    except (KeyboardInterrupt, EOFError):
        print
        print '[Interrupted.]'
        return

if __name__ == "__main__":
    main(sys.argv)