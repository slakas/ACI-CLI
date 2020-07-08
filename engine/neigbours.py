#!/usr/bin/env python

"""
Simple application that logs on to the APIC, pull all CDP neighbours,
and display in text table format
"""
import time
import sys
import engine.acitoolkit.acitoolkit as ACI
from acitoolkit import Node
from engine.acitoolkit.aciConcreteLib import ConcreteCdp
from engine.acitoolkit.aciConcreteLib import ConcreteLLdp


class NEIGHBOURS():
    """docstring for Endpoint."""

    def __init__(self, session, logging=None, bcolors=None):
        self.endpoints_data = []
        # session to APIC
        self.session = session
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors

    def get_nodes_object(self, node = None):
        self.logging.info("get nodes")

        if not node:
            nodes = Node.get_deep(self.session, include_concrete=True)
        else:
            nodes = Node.get(self.session, None, node)

        self.logging.info("Got it")

        return nodes


    # Get CDP neighbours
    def cdp(self, node = None):
        cdps = []
        self.logging.info("node_concrete_cdp")

        if not node:
            nodes = self.get_nodes_object()
        else:
            nodes = self.get_nodes_object(node)

        for node in nodes:
            node_concrete_cdp = node.get_children(child_type=ConcreteCdp)
            for node_concrete_cdp_obj in node_concrete_cdp:
                cdps.append(node_concrete_cdp_obj)


        tables = ConcreteCdp.get_table(cdps)
        output_list = []
        # for i in progressbar(range(len(tables)), "Computing: ", 40):
        #     time.sleep(0.1) # any calculation you need
        for table in tables:
            for table_data in table.data:
                if table_data not in output_list:
                    output_list.append(table_data)

        return output_list



    def lldp(self, node = None):
        lldps = []

        self.logging.info("node_concrete_lldp")

        if not node:
            nodes = self.get_nodes_object()
        else:
            nodes = self.get_nodes_object(node)

        for node in nodes:
            node_concrete_lldp = node.get_children(child_type=ConcreteLLdp)
            for node_concrete_lldp_obj in node_concrete_lldp:
                lldps.append(node_concrete_lldp_obj)

        tables = ConcreteLLdp.get_table(lldps)
        output_list = []
        for table in tables:
            for table_data in table.data:
                if table_data not in output_list:
                    output_list.append(table_data)

        return output_list
