'''
Pyste version %s

Usage:
    pyste [options] --module=<name> interface-files

where options are:
    -I <path>           add an include path
    -D <symbol>         define symbol
    --no-using          do not declare "using namespace boost";
                        use explicit declarations instead
    --pyste-ns=<name>   set the namespace where new types will be declared;
                        default is "pyste"
    -h, --help          print this help and exit
    -v, --version       print version information                         
'''

import sys
import os
import getopt
import exporters
import CodeUnit
import infos
import exporterutils
import settings
from policies import *
from CppParser import CppParser, CppParserError
import time

__VERSION__ = '0.6.4'

def GetDefaultIncludes():
    if 'INCLUDE' in os.environ:
        include = os.environ['INCLUDE']
        return include.split(os.pathsep)
    else:
        return []


def ParseArguments():

    def Usage():
        print __doc__ % __VERSION__
        sys.exit(1)
        
    try:
        options, files = getopt.getopt(
            sys.argv[1:], 
            'I:D:vh', 
            ['module=', 'out=', 'no-using', 'pyste-ns=', 'debug', 'version', 'help'])
    except getopt.GetoptError, e:
        print
        print 'ERROR:', e
        Usage()
    includes = GetDefaultIncludes()
    defines = []
    module = None
    out = None
    for opt, value in options:
        if opt == '-I':
            includes.append(value)
        elif opt == '-D':
            defines.append(value)
        elif opt == '--module':
            module = value
        elif opt == '--out':
            out = value 
        elif opt == '--no-using':
            settings.namespaces.python = 'boost::python::'
            CodeUnit.CodeUnit.USING_BOOST_NS = False
        elif opt == '--pyste-ns':
            settings.namespaces.pyste = value + '::'
        elif opt == '--debug':
            settings.DEBUG = True
        elif opt in ['-h', '--help']:
            Usage()
        elif opt in ['-v', '--version']:
            print 'Pyste version %s' % __VERSION__
            sys.exit(2)
        else:
            print 'Unknown option:', opt
            Usage()

    if not files or not module:
        Usage()
    if not out:
        out = module + '.cpp'
    return includes, defines, module, out, files

    
def CreateContext():
    'create the context where a interface file can be executed'
    context = {}
    # infos
    context['Function'] = infos.FunctionInfo
    context['Class'] = infos.ClassInfo
    context['Include'] = infos.IncludeInfo
    context['Template'] = infos.ClassTemplateInfo
    context['Enum'] = infos.EnumInfo
    context['AllFromHeader'] = infos.HeaderInfo
    # functions
    context['rename'] = infos.rename
    context['set_policy'] = infos.set_policy
    context['exclude'] = infos.exclude
    context['set_wrapper'] = infos.set_wrapper
    context['use_shared_ptr'] = infos.use_shared_ptr
    context['use_auto_ptr'] = infos.use_auto_ptr
    # policies
    context['return_internal_reference'] = return_internal_reference
    context['with_custodian_and_ward'] = with_custodian_and_ward
    context['return_value_policy'] = return_value_policy
    context['reference_existing_object'] = reference_existing_object
    context['copy_const_reference'] = copy_const_reference
    context['copy_non_const_reference'] = copy_non_const_reference
    context['manage_new_object'] = manage_new_object
    # utils
    context['Wrapper'] = exporterutils.FunctionWrapper
    return context                                        

    
def Main():
    includes, defines, module, out, interfaces = ParseArguments()
    # execute the interface files
    for interface in interfaces:
        context = CreateContext()
        execfile(interface, context)        
    # parse all the C++ code        
    parser = CppParser(includes, defines) 
    exports = exporters.exporters[:]
    for export in exports:
        try:
            export.Parse(parser)
        except CppParserError, e:            
            print '\n'
            print '***', e, ': exitting'
            return 2
    print 
    # sort the exporters by its order
    exports = [(x.Order(), x) for x in exporters.exporters]
    exports.sort()
    exports = [x for _, x in exports]
    # now generate the wrapper code
    codeunit = CodeUnit.CodeUnit(module)
    exported_names = []
    for export in exports:
        export.GenerateCode(codeunit, exported_names)    
        exported_names.append(export.Name())
    codeunit.Save(out)                
    print 'Module %s generated' % module
    return 0


def UsePsyco():
    'Tries to use psyco if possible'
    try:
        import psyco
        psyco.profile()
    except: pass         

    
if __name__ == '__main__':
    start = time.clock()
    UsePsyco()
    status = Main()
    print '%0.2f seconds' % (time.clock()-start)
    sys.exit(status)
