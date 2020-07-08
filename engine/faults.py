#!/usr/bin/env python

"""
simple application that logs on to apic and displays all the faults.
if a particular tenant is given shows faults of that tenant
and if a domain is given displays faults related to that domain.
list of domains can also be given
"""
from acitoolkit import (Credentials, Session, Faults)


class ShowFaults():
    """docstring for aci-show-faults-by-domain"""
    description = 'Simple application that logs on to the APIC and displays all of the Tenants.'

    def __init__(self, session, tenant=None, domain=None):
        # session to APIC
        self.session = session
        self.tenant = tenant
        self.domain_name = domain

    def by_domain(self):
        faults_obj = Faults()
        fault_filter = None
        if self.domain_name is not None:
            fault_filter = {'domain': self.domain_name.split(',')}

        tenant_name = None
        if self.tenant is not None:
            tenant_name = self.tenant.name

        faults_obj.subscribe_faults(self.session, fault_filter)
        # while faults_obj.has_faults(session, fault_filter) or args.continuous:
        while faults_obj.has_faults(self.session, fault_filter):
            if faults_obj.has_faults(self.session, fault_filter):
                faults = faults_obj.get_faults(
                    self.session, fault_filter=fault_filter, tenant_name=tenant_name)
                if faults is not None:
                    for fault in faults:
                        if fault is not None:
                            print("---------------")
                            if fault.descr is not None:
                                print("     descr     : " + fault.descr)
                            else:
                                print("     descr     : " + "  ")
                            print("     dn        : " + fault.dn)
                            print("     rule      : " + fault.rule)
                            print("     severity  : " + fault.severity)
                            print("     type      : " + fault.type)
                            print("     domain    : " + fault.domain)

    def clear(self):
        self.session = None
        self.tenant = None
        self.domain_name = None
