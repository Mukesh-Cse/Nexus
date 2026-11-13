import unittest,importlib.util
from pathlib import Path
from nexus.database.workspace import session_repository

class DeploymentTests(unittest.TestCase):
    def test_public_visitors_have_separate_profiles(self):
        first={};second={}
        a=session_repository(first);b=session_repository(second)
        try:
            c=a.company("baltic")
            c.priority="Visitor one experiment"
            a.save_company(c,expected_revision=c.revision)
            self.assertEqual(a.company("baltic").priority,"Visitor one experiment")
            self.assertEqual(b.company("baltic").priority,"")
        finally:
            a.close();b.close()
    def test_same_session_retains_workspace(self):
        state={}
        a=session_repository(state)
        try:self.assertIs(a,session_repository(state))
        finally:a.close()
    def test_feedback_is_session_isolated(self):
        a=session_repository({});b=session_repository({})
        try:
            a.feedback("dnv","hypothesis",4,"A demo response")
            self.assertEqual(len(a.feedback_rows()),1)
            self.assertEqual(len(b.feedback_rows()),0)
        finally:a.close();b.close()
    def test_hosting_port_command(self):
        path=Path(__file__).resolve().parents[1]/"scripts"/"serve.py"
        spec=importlib.util.spec_from_file_location("nexus_serve",path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        args=mod.command({"PORT":"12345"})
        self.assertIn("--server.address=0.0.0.0",args)
        self.assertIn("--server.port=12345",args)
        with self.assertRaises(ValueError):mod.command({"PORT":"70000"})

