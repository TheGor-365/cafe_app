#!/usr/bin/env python3
"""No Docker access. Regression tests for known readonly Cafe test Rails mounts."""
import copy
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[2]/"scripts/cafe_p12_reboot_private_test_rails_20261106.py"
spec=importlib.util.spec_from_file_location("cafe_p12_reboot_mount_gate",SOURCE)
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def fixture():
    label,name,network,url,readonly=gate.CANDIDATES[0]
    private=gate.PRIVATE
    target={
      "Name":"/"+name,
      "State":{"Status":"exited"},
      "Config":{"Image":gate.IMAGE,"User":"1000:1000",
                "Env":["DATABASE_URL="+url,"BUNDLE_GEMFILE=/app/Gemfile",
                       "RAILS_ENV=development"]},
      "HostConfig":{"ReadonlyRootfs":True,"RestartPolicy":{"Name":"no"},
                    "PortBindings":None},
      "NetworkSettings":{"Networks":{network:{}}},
      "Mounts":[
         {"Destination":"/app","Type":"bind",
          "Source":str(private/"reviewed_source"),"RW":False},
         {"Destination":"/app/public/uploads","Type":"bind",
          "Source":str(private/"uploads_security_sandbox_20261104"),"RW":True},
         {"Destination":"/bundle","Type":"bind",
          "Source":str(private/"bundle_carrierwave_227_20261104"),"RW":False},
         {"Destination":"/usr/local/lib/ruby/gems","Type":"volume",
          "Name":"cafe-legacy-dependency-readonly","RW":False},
      ],
    }
    return label,name,network,url,readonly,target

class Inventory:
    def __init__(self, obj):self.obj=obj
    def inspect(self, kind, name):
        assert kind=="container" and name==self.obj["Name"].lstrip("/")
        return self.obj

class TestMountContract(unittest.TestCase):
    def check_target(self, mutate=None):
        label,name,network,url,readonly,obj=fixture()
        if mutate: mutate(obj)
        return gate.inspect_web(Inventory(obj),label,name,network,url,readonly)

    def test_readonly_named_dependency_volume_allowed(self):
        self.assertEqual(self.check_target(),"exited")

    def test_writable_named_volume_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"source/media mount scope"):
            self.check_target(lambda o:o["Mounts"][3].update(RW=True))

    def test_volume_without_name_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"source/media mount scope"):
            self.check_target(lambda o:o["Mounts"][3].update(Name=""))

    def test_unknown_mount_type_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"source/media mount scope"):
            self.check_target(lambda o:o["Mounts"][3].update(Type="device"))

    def test_wrong_private_media_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"private media"):
            self.check_target(lambda o:o["Mounts"][1].update(Source="/tmp/unknown-uploads"))

    def test_writable_source_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"source/media mount scope"):
            self.check_target(lambda o:o["Mounts"][0].update(RW=True))

    def test_published_port_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"runtime differs"):
            self.check_target(lambda o:o["HostConfig"].update(PortBindings={"3001/tcp":[{"HostIp":"0.0.0.0","HostPort":"3001"}]}))

    def test_prod_network_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"runtime differs"):
            self.check_target(lambda o:o["NetworkSettings"]["Networks"].update({"cafe-app-private":{}}))

    def test_wrong_bundle_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"frozen Ruby bundle"):
            self.check_target(lambda o:o["Mounts"][2].update(Source="/unknown"))

    def test_legacy_qa_secret_mount_blocked(self):
        with self.assertRaisesRegex(RuntimeError,"source/media mount scope"):
            self.check_target(lambda o:o["Mounts"].append({"Destination":"/run/secrets/cafe_pg_password","Type":"bind","Source":"/tmp/fake","RW":False}))

if __name__=="__main__":
    unittest.main()
