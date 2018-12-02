# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.settings import settings
from octoprint.server.util.flask import restricted_access

import flask, json
import os.path

class PrintQueuePlugin(octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.EventHandlerPlugin):

    _print_queue = []
    _print_completed = False
    _uploads_dir = settings().getBaseFolder("uploads")


    # BluePrintPlugin (api requests)
    @octoprint.plugin.BlueprintPlugin.route("/queue", methods=["GET"])
    def get_queue(self):
        self._logger.info("PQ: getting queue")
        return flask.jsonify(print_queue=self._print_queue)

    @octoprint.plugin.BlueprintPlugin.route("/queue", methods=["POST"])
    @restricted_access
    def set_queue(self):
        self._logger.info("PQ: received print queue from frontend")
        last_print_queue = self._print_queue[:]

        self._print_queue = []
        for v in flask.request.form:
            j = json.loads(v)
            for p in j:
                self._print_queue.append(p)

        state = self._printer.get_state_id()
        if state in ["PRINTING", "PAUSED"]:
            # keep the currently active job on the top of the queue
            active_file = self._printer.get_current_job()["file"]["path"]
            if not self._print_queue or self._print_queue[0] != active_file:
                try:
                    self._print_queue.remove(active_file)
                except ValueError:
                    pass
                self._print_queue.insert(0, active_file)
                if self._print_queue == last_print_queue:
                    # force correcting the queue on the originating client
                    last_print_queue = []

        if self._print_queue != last_print_queue:
            self._send_queue_to_clients()

        if state  == "OPERATIONAL" and self._settings.get(["auto_start_queue"]):
            self._print_from_queue()

        return flask.make_response("POST successful", 200)

    @octoprint.plugin.BlueprintPlugin.route("/start", methods=["POST"])
    @restricted_access
    def start_queue(self):
        self._print_queue = []
        for v in flask.request.form:
            j = json.loads(v)
            for p in j:
                self._print_queue += [p]

        self._print_from_queue()

        return flask.make_response("POST successful", 200)

    def _print_from_queue(self):
        if len(self._print_queue) > 0:
            f = os.path.join(self._uploads_dir, self._print_queue[0])
            self._logger.info("PQ: attempting to select and print file: " + f)
            self._printer.select_file(f, False, True)


    def _send_queue_to_clients(self):
        self._plugin_manager.send_plugin_message(self._identifier, dict(
            type="set_queue",
            print_queue=self._print_queue
        ))


    # SettingPlugin
    def get_settings_defaults(self):
        return dict(
            bed_clear_script="",
            auto_start_queue=False,
            auto_queue_files=True
        )

    # TemplatePlugin
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False, template="print_queue_settings.jinja2"),
        ]

    # AssetPlugin
    def get_assets(self):
        return dict(
            js=["js/jquery-ui.min.js", "js/knockout-sortable.js", "js/print_queue.js"]
    )


    # Hooks
    def alter_print_completion_script(self, comm_instance, script_type, script_name, *args, **kwargs):
        if script_type == "gcode" and script_name == "afterPrintDone" and len(self._print_queue) > 0:
            prefix = self._settings.get(["bed_clear_script"])
            postfix = None
            return prefix, postfix
        else:
            return None

    def alter_start_and_end_gcode(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
        # TODO: strip start & end code up to settable markers
        pass

    # Event Handling
    def on_event(self, event, payload):
        if event == "ClientOpened":
            self._send_queue_to_clients()

        if event == "FileAdded":
            if self._settings.get(["auto_queue_files"]):
                self._print_queue.append(payload["path"])
                self._send_queue_to_clients()

        if event == "FileRemoved":
            new_queue = [f for f in self._print_queue if f != payload["path"]]
            if new_queue != self._print_queue:
                self._print_queue = new_queue
                self._send_queue_to_clients()

        if event == "PrintStarted":
            self._print_completed = False

            if not self._print_queue or self._print_queue[0] != payload["path"]:
                self._print_queue.insert(0, payload["path"])
                self._send_queue_to_clients()

        if event == "PrintDone":
            self._print_completed = True

        if event == "PrinterStateChanged":
            state = self._printer.get_state_id()
            self._logger.info("printer state: " + state)
            if state  == "OPERATIONAL":
                if self._print_completed and len(self._print_queue) > 0:
                    self._print_queue.pop(0)
                    self._send_queue_to_clients()

                    if len(self._print_queue) > 0:
                        self._print_from_queue()

        return

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            print_queue=dict(
                displayName="Print Queue",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="blackbelt3d",
                repo="OctoPrint-Print-Queue",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/blackbelt3d/OctoPrint-Print-Queue/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "Print Queue"
def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintQueuePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.scripts": __plugin_implementation__.alter_print_completion_script,
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.alter_start_and_end_gcode,
    }
