import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT = (Path(__file__).resolve().parents[2] / "scripts" /
          "cafe_rc71_isolated_preview_20261108.py")
SPEC = importlib.util.spec_from_file_location("cafe_rc71_preview", SCRIPT)
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)

WEB_IMAGE_ID = "sha256:" + "a" * 64
DB_IMAGE_ID = "sha256:" + "b" * 64


class CafeRc71PreviewOperatorTest(unittest.TestCase):
    def test_pg_command_is_offline_named_and_isolated(self):
        command = preview.pg_run_command(DB_IMAGE_ID)

        self.assertEqual(command[:4], ["docker", "run", "--pull=never", "-d"])
        self.assertEqual(command[-1], DB_IMAGE_ID)
        self.assertIn(preview.NET, command)
        self.assertIn(preview.PG_VOLUME, " ".join(command))
        self.assertNotIn(preview.DB_IMAGE, command)

    def test_private_bundle_seed_reads_shared_volume_and_install_has_no_ports(self):
        seed = preview.bundle_seed_command("shared-bundle", WEB_IMAGE_ID)
        setup = preview.bundle_setup_command(WEB_IMAGE_ID)

        self.assertIn("none", seed)
        self.assertIn("type=volume,source=shared-bundle,target=/source-bundle,readonly",
                      seed)
        self.assertIn("type=volume,source=" + preview.BUNDLE_VOLUME + ",target=/bundle",
                      seed)
        self.assertIn("bundle install --jobs 2 --retry 2 && bundle check", setup[-1])
        self.assertIn("BUNDLE_LOCAL__DEVISE=/vendor/devise", setup)
        self.assertIn("BUNDLE_FROZEN=false", setup)
        self.assertIn("target=/app/Gemfile.lock", " ".join(setup))
        self.assertIn("bundle lock --add-platform x86_64-linux", setup[-1])
        self.assertIn("1000:1000", setup)
        self.assertIn("chown -R 1000:1000 /bundle", seed[-1])
        self.assertIn("CHOWN", seed)
        self.assertIn("none", seed)
        self.assertNotIn("--publish", seed)
        self.assertNotIn("--publish", setup)
        self.assertEqual(seed[:3], ["docker", "run", "--pull=never"])
        self.assertEqual(setup[:3], ["docker", "run", "--pull=never"])

    def test_setup_and_web_commands_keep_source_readonly_and_port_loopback_only(self):
        setup = preview.setup_run_command("bundle-volume", "node-volume",
                                          WEB_IMAGE_ID, "true")
        web = preview.web_run_command("bundle-volume", "node-volume",
                                      WEB_IMAGE_ID)

        for command in (setup, web):
            self.assertEqual(command[:3], ["docker", "run", "--pull=never"])
            self.assertIn("--read-only", command)
            self.assertIn("no-new-privileges", command)
            self.assertIn("ALL", command)
            self.assertIn(preview.NET, command)
            self.assertIn(WEB_IMAGE_ID, command)
            mounts = [command[index + 1] for index, value in enumerate(command)
                      if value == "--mount"]
            self.assertTrue(any("target=/app,readonly" in value for value in mounts))
            self.assertTrue(any("target=/bundle,readonly" in value for value in mounts))
            self.assertTrue(any("target=/app/node_modules,readonly" in value
                                for value in mounts))

        self.assertNotIn("127.0.0.1:3003:3003", web)
        self.assertNotIn(preview.IMAGE, web)

    def test_rails_pid_is_container_private_and_not_shared_with_owner_checkout(self):
        web = preview.web_run_command("private-bundle", "node-volume", WEB_IMAGE_ID)
        self.assertIn("--pid /tmp/cafe-rc71-server.pid", web[-1])
        self.assertNotIn("/app/tmp/pids/server.pid", web[-1])
        self.assertIn("--tmpfs", web)
        self.assertIn("/tmp:rw,size=128m,mode=1777", web)

    def test_readonly_post_e2e_verifier_accepts_recorded_orders(self):
        with mock.patch.object(preview, "sql", side_effect=["0", "0"]) as sql:
            self.assertEqual(preview.preview_order_count(), 0)
            self.assertEqual(sql.call_count, 2)
        with mock.patch.object(preview, "sql", side_effect=["8", "0"]) as sql:
            self.assertEqual(preview.preview_order_count(), 8)
            self.assertEqual(sql.call_count, 2)

    def test_post_e2e_verifier_rejects_bad_count_and_unknown_statuses(self):
        for results in (["not-a-count", "0"], ["2", "1"]):
            with self.subTest(results=results):
                with mock.patch.object(preview, "sql", side_effect=results):
                    with self.assertRaises(preview.Stop):
                        preview.preview_order_count()

    def test_stateless_proxy_is_only_loopback_publisher(self):
        proxy = preview.proxy_run_command(WEB_IMAGE_ID)
        self.assertIn("127.0.0.1:3003:3003", proxy)
        self.assertNotIn("0.0.0.0:3003:3003", proxy)
        self.assertIn(preview.ACCESS_NET, proxy)
        self.assertIn("--read-only", proxy)
        self.assertIn("ALL", proxy)
        self.assertNotIn("--mount", proxy)
        self.assertNotIn("--env-file", proxy)

    def test_nested_readonly_bind_mountpoints_are_declared(self):
        self.assertEqual(set(preview.SOURCE_MOUNTPOINTS),
                         {"node_modules", "public/packs", "public/uploads",
                          "tmp", "log"})
        mount_targets = {value.split("target=", 1)[1].split(",", 1)[0]
                         for value in preview.mount_args("bundle", "node")
                         if "target=" in value}
        for folder in preview.SOURCE_MOUNTPOINTS:
            self.assertIn("/app/" + folder, mount_targets)
        self.assertIn("/vendor/devise", mount_targets)
        self.assertIn("/app/Gemfile.lock", mount_targets)

    def test_pinned_git_dependency_is_immutable(self):
        self.assertEqual(preview.DEVISE_REVISION,
                         "e16d60d0fedc5f5e6f541b2b9e901a2d53f8ceda")
        self.assertEqual(preview.DEVISE_BRANCH, "ca-omniauth-2")
        self.assertTrue(preview.DEVISE_REPO.startswith("https://github.com/"))

    def test_image_ids_must_be_immutable_sha256_values(self):
        self.assertEqual(preview.image_id(WEB_IMAGE_ID), WEB_IMAGE_ID)
        for unsafe in (preview.IMAGE, preview.DB_IMAGE, "sha256:short", ""):
            with self.assertRaises(preview.Stop):
                preview.image_id(unsafe)

    def test_git_clean_rejects_tracked_and_untracked_changes(self):
        with mock.patch.object(preview, "execute",
                               return_value=SimpleNamespace(stdout=b"")):
            self.assertTrue(preview.git_clean(Path("/tmp/source")))
        with mock.patch.object(preview, "execute",
                               return_value=SimpleNamespace(stdout=b"?? surprise\n")):
            self.assertFalse(preview.git_clean(Path("/tmp/source")))

    def test_pg_wait_requires_two_sql_successes_from_same_postmaster(self):
        values = [
            SimpleNamespace(returncode=2, stdout=b""),
            SimpleNamespace(returncode=0, stdout=b"cafe|temporary\n"),
            SimpleNamespace(returncode=0, stdout=b"cafe|final\n"),
            SimpleNamespace(returncode=0, stdout=b"cafe|final\n"),
        ]
        with mock.patch.object(preview, "execute", side_effect=values) as execute:
            with mock.patch.object(preview.time, "sleep"):
                preview.wait_pg()
        self.assertEqual(execute.call_count, 4)
        self.assertTrue(all("psql" in call.args for call in execute.call_args_list))

    def test_operator_source_contains_no_destructive_cleanup(self):
        source = SCRIPT.read_text()
        for forbidden in ("docker rm ", "docker stop ", "db:drop", "db:reset",
                          "git reset --hard", "git clean -fd",
                          "docker compose down"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("bundle exec rails db:schema:load", source)
        self.assertIn("load Rails.root.join('db/schema.rb')", source)


if __name__ == "__main__":
    unittest.main()
