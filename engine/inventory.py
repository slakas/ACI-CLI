#!/usr/bin/env python
# -*- encoding: utf-8 -*-
### INTERFACEs MODULE

import engine.acitoolkit.acitoolkit as aci
import json
import time
import sys


class CollectInventory():
    def __init__(self, session, logging, bcolors):
        # session to APIC
        self.session = session
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors

    def _get_query(self, query_url, error_msg):
        resp = self.session.get(query_url)
        if not resp.ok:
            self.logging.warning(error_msg)
            self.logging.warning(resp.text)
            return None
        return resp.json()

    def get_nodes(self, node_id=None):
        """
        Get the list of nodes ids
        :return: dictionaty of strings containing node ids and dicts of node details
        """


        nodes_data = {}
        query_url = ('/api/node/class/fabricNode.json?'
                     'query-target-filter=eq(fabricNode.role,"leaf")')
        resp = self.session.get(query_url)
        if not resp.ok:
            print('Could not get switch list from APIC.')
            return
        nodes = resp.json()['imdata']
        for node in nodes:
            if (node_id and str(node['fabricNode']['attributes']['id']) == node_id) or not node_id:
                nodes_data.update({str(node['fabricNode']['attributes']['id']): node['fabricNode']['attributes']})

        return nodes_data

    def get_all_inserted_sfps(self, node_id=None):
        sfps = []
        inf_details = []
        interfaces = None
        # get all nodes
        nodes = self.get_nodes(node_id)
        # setup toolbar
        toolbar_width = len(nodes)
        sys.stdout.write("[%s]" % (" " * toolbar_width))
        sys.stdout.flush()
        sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

        for key, value in nodes.items():
            url = ('/api/mo/'+str(value['dn'])+'/sys.json?query-target=subtree'
                         '&target-subtree-class=l1PhysIf')
            error_message = 'Could not collect APIC data for switch %s.' % key
            interfaces = self._get_query(url, error_message)

            if not interfaces:
                continue

            # print(json.dumps(interfaces, indent=4, sort_keys=True))
            for interface in interfaces['imdata']:
                inf_details = []
                inf_media_dn = '/api/mo/'+str(interface['l1PhysIf']['attributes']['dn'])+'/phys/fcot'
                sfp = self.get_interface_media_attributes(inf_media_dn)
                if sfp:
                    inf_details.append(key)
                    inf_details.append(str(interface['l1PhysIf']['attributes']['id']))
                    inf_details.append(sfp['typeName'])         #QSFP-100G-AOC50M
                    inf_details.append(sfp['guiPN'])            # part number
                    inf_details.append(sfp['guiSN'])            #serial number
                    inf_details.append(sfp['guiRev'])

                    sfps.append(tuple(inf_details))

            # progress bar
            sys.stdout.write("#")
            sys.stdout.flush()

        sys.stdout.write("]\n") # this ends the progress bar

        return sfps

    def get_interface_media_attributes(self, url):
        #
        url += '.json'
        error_message = 'Could not collect APIC data '
        media = self._get_query(url, error_message)
        for sfp in media['imdata']:
            if sfp["ethpmFcot"]["attributes"]['state'] == "inserted":
                return sfp["ethpmFcot"]["attributes"]

        return None
