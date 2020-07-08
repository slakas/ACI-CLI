#!/usr/bin/env python


"""
Simple application that logs on to the APIC and displays all
of the Interfaces.
"""
from operator import attrgetter
import sys
import engine.acitoolkit.acitoolkit as ACI


class INTERAFES_STATS:


    def __init__(self, session, logging, bcolors):
        # session to APIC
        self.session = session
        # get Intercaes
        self.interfaces = aci.Interface.get(self.session)
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors


    def show_stats_short(self, args, interfaces, granularity='5min', epoch=0):
        """
        show stats short routine

        :param args: command line arguments
        :param interfaces: list of interfaces
        :return: None
        """
        # setup template and display header information
        template = "{0:17} {1:12} {2:12} {3:16} {4:16} {5:16} {6:16}"
        print('Granularity: ' + str(granularity) + ' Epoch:' + str(epoch))
        print(template.format("   INTERFACE  ", "TOT RX PACKETS", "TOT TX PACKETS", "RX PKTs/Sec", "TX PKTs/Sec", "RX BYTES/Sec", "TX BYTES/Sec"))
        print(template.format("--------------", "------------ ", "------------ ", "---------------",
                              "---------------", "---------------", "---------------"))
        template = "{0:17} {1:12,} {2:12,} {3:16,.2f} {4:16,.2f} {5:16,.2f} {6:16,.2f}"

        for interface in sorted(interfaces, key=attrgetter('if_name')):
            interface.stats.get()

            rec = []
            allzero = True
            for (counter_family, counter_name) in [('ingrTotal', 'pktsAvg'), ('egrTotal', 'pktsAvg'),
                                                   ('ingrTotal', 'pktsRateAvg'), ('egrTotal', 'pktsRateAvg'),
                                                   ('ingrTotal', 'bytesRateAvg'), ('egrTotal', 'bytesRateAvg')]:

                rec.append(interface.stats.retrieve(counter_family, granularity, epoch, counter_name))
                if interface.stats.retrieve(counter_family, granularity, epoch, counter_name) != 0:
                    allzero = False

            if (args.nonzero and not allzero) or not args.nonzero:
                print(template.format(interface.name, *rec))


    def show_stats_long(self, args, interfaces, granularity='5min', epoch=0):
        """
        show stats long routine

        :param args: command line arguments
        :param interfaces: list of interfaces
        :return: None
        """
        print('Interface {0}/{1}/{2}/{3}  Granularity:{4} Epoch:{5}'.format(interfaces[0].pod,
                                                                            interfaces[0].node,
                                                                            interfaces[0].module,
                                                                            interfaces[0].port,
                                                                            granularity,
                                                                            epoch))
        stats = interfaces[0].stats.get()
        for stats_family in sorted(stats):
            print(stats_family)
            if args.granularity in stats[stats_family]:
                if epoch in stats[stats_family][granularity]:
                    for counter in sorted(stats[stats_family][granularity][epoch]):
                        print('    {0:>16}: {1}'.format(counter,
                                                        stats[stats_family][granularity][epoch][counter]))


    def get_stats(self, interface=None):
            # Download all of the interfaces and get their stats
            # and display the stats
            if interface:
                interface = interface
                if 'eth ' in interface:
                    interface = interface[4:]
                (pod, node, module, port) = interface.split('/')
                interfaces = ACI.Interface.get(self.session, pod, node, module, port)
            else:
                interfaces = ACI.Interface.get(self.session)

            if not args.full or not args.interface:
                show_stats_short(args, interfaces)
            else:
                show_stats_long(args, interfaces)


def main():
    """
    Main execution routine

    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = 'Simple application that logs on to the APIC and displays stats for all of the Interfaces.'
    creds = ACI.Credentials('apic', description)
    creds.add_argument('-i', '--interface',
                       type=str,
                       help='Specify a particular interface node/pod/module/port e.g. 1/201/1/21')
    creds.add_argument('-e', '--epoch', type=int,
                       default=0,
                       help='Show a particular epoch (default=0)')
    creds.add_argument('-g', '--granularity', type=str,
                       default='5min',
                       help='Show a particular granularity (default="5min")')
    creds.add_argument('-f', '--full', action="store_true",
                       help='Show full statistics - only available if interface is specified')
    creds.add_argument('-n', '--nonzero', action='store_true',
                       help='Show only interfaces where the counters are not zero. - only available if interface is NOT specified')
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    # Download all of the interfaces and get their stats
    # and display the stats
    if args.interface:
        interface = args.interface
        if 'eth ' in interface:
            interface = interface[4:]
        (pod, node, module, port) = interface.split('/')
        interfaces = ACI.Interface.get(session, pod, node, module, port)
    else:
        interfaces = ACI.Interface.get(session)

    if not args.full or not args.interface:
        show_stats_short(args, interfaces)
    else:
        show_stats_long(args, interfaces)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
