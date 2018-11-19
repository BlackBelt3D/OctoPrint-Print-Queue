# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.settings import settings
import flask, json
import os.path

class PrintQueuePlugin(octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.EventHandlerPlugin):

    printqueue = []
    selected_file = ""
    uploads_dir = settings().getBaseFolder("uploads")

    # BluePrintPlugin (api requests)
    @octoprint.plugin.BlueprintPlugin.route("/addselectedfile", methods=["GET"])
    def add_selected_file(self):
        self._logger.info("PQ: adding selected file: " + self.selected_file)
        self._printer.unselect_file()
        f = self.selected_file
        self.selected_file = ""
        return flask.jsonify(filename=f)

    @octoprint.plugin.BlueprintPlugin.route("/clearselectedfile", methods=["POST"])
    def clear_selected_file(self):
        self._logger.info("PQ: clearing selected file")
        self._printer.unselect_file()
        self.selected_file = ""
        return flask.make_response("POST successful", 200)

    @octoprint.plugin.BlueprintPlugin.route("/printcontinuously", methods=["POST"])
    def print_continuously(self):
        self.printqueue = []
        for v in flask.request.form:
            j = json.loads(v)
            for p in j:
                self.printqueue += [p]

        f = os.path.join(self.uploads_dir, self.printqueue[0])
        self._logger.info("PQ: attempting to select and print file: " + f)
        self._printer.select_file(f, False, True)
        self.printqueue.pop(0)
        return flask.make_response("POST successful", 200)

    # SettingPlugin
    def get_settings_defaults(self):
        return dict(bed_clear_script="")

    # TemplatePlugin
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False, template="print_queue_settings.jinja2"),
        ]

    # AssetPlugin
    def get_assets(self):
        return dict(
            js=["js/print_queue.js"]
    )


    # Hooks
    def print_completion_script(self, comm, script_type, script_name, *args, **kwargs):
        if script_type == "gcode" and script_name == "afterPrintDone" and len(self.printqueue) > 0:
            prefix = self._settings.get(["bed_clear_script"])
            postfix = None
            return prefix, postfix
        else:
            return None

    # Event Handling
    def on_event(self, event, payload):
        if event == "FileSelected":
            self._plugin_manager.send_plugin_message(self._identifier, dict(message="file_selected",file=payload["path"]))
            self.selected_file = payload["path"]
        if event == "PrinterStateChanged":
            state = self._printer.get_state_id()
            if state  == "OPERATIONAL" and len(self.printqueue) > 0:
                self._logger.info("selecting next print from queue")
                self._printer.select_file(os.path.join(self.uploads_dir, self.printqueue[0]), False, True)
                self.printqueue.pop(0)
            if state == "OFFLINE" or state == "CANCELLING" or state == "CLOSED" or state == "ERROR" or state == "CLOSED_WITH_ERROR":
                self._logger.info("deleting print queue")
                self.printqueue = []

        return

__plugin_name__ = "Print Queue"
def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintQueuePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.scripts": __plugin_implementation__.print_completion_script,
    }
