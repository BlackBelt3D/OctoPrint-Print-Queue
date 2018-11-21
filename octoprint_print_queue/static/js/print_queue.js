/*
 * View model for OctoPrint-Print-Queue
 *
 * Author: Michael New
 * License: AGPLv3
 */

$(function() {
    function PrintQueueViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.bedClearScript = ko.observable();
        self.queuedPrints = ko.observableArray([]);

        self.createPrintQueueString = function() {
            let printList = [];
            for (var i = 0; i < self.queuedPrints().length; i++) {
                let fileName = self.queuedPrints()[i]["fileName"];
                let count = self.queuedPrints()[i]["printNumber"];
                for (var j = 0; j < count; j++) {
                    printList.push(fileName);
                }
            }
            return printList;
        }

        self.printContinuously = function() {
            console.log(self.createPrintQueueString());
            $.ajax({
                url: "plugin/print_queue/printcontinuously",
                type: "POST",
                dataType: "json",
                headers: {
                    "X-Api-Key":UI_API_KEY,
                },
                data: JSON.stringify(self.createPrintQueueString()),
                success: self.postResponse
            });
        }

        self.changePrintNumber = function(data) {
            console.log('PQ: not yet implemented');
            console.log(data);
        }

        self.removeFile = function(file) {
            self.queuedPrints.remove(file);
        }

        self.addSelectedFile = function() {
            $.ajax({
                url: "plugin/print_queue/addselectedfile",
                type: "GET",
                dataType: "json",
                headers: {
                    "X-Api-Key":UI_API_KEY,
                },
                success: self.addFileResponse
            });
        }

        self.clearSelectedFile = function() {
            $.ajax({
                url: "plugin/print_queue/clearselectedfile",
                type: "POST",
                dataType: "json",
                headers: {
                    "X-Api-Key":UI_API_KEY,
                },
                success: self.postResponse
            });
        }

        self.addFileResponse = function(data) {
            console.log('PQ: add file success');
            console.log(data);
            let f = data["filename"]
            if (f) {
                    self.queuedPrints.push({fileName: f, printNumber: 1})
            } else {
                    self.queuedPrints.push({fileName: "", printNumber: 1})
            }
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            // if the "add file" field is blank and the user loads a new file
            // put it's name into the text field
            if (plugin == "print_queue" && data["message"] == "file_selected") {
                let l = self.queuedPrints().length;
                if (l > 0) {
                    let last = self.queuedPrints()[l - 1];
                    console.log(last["fileName"]);
                    if (last["fileName"] == "") {
                        self.queuedPrints.replace(last, {fileName: data["file"], printNumber: last["printNumber"]})
                        self.clearSelectedFile();
                    }
                }
            }
        }
    }

    // This is how our plugin registers itself with the application, by adding some configuration
    // information to the global variable OCTOPRINT_VIEWMODELS
    OCTOPRINT_VIEWMODELS.push([
        // This is the constructor to call for instantiating the plugin
        PrintQueueViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request
        // here is the order in which the dependencies will be injected into your view model upon
        // instantiation via the parameters argument
        ["settingsViewModel"],

        // Finally, this is the list of selectors for all elements we want this view model to be bound to.
        ["#tab_plugin_print_queue"]
    ]);
});
