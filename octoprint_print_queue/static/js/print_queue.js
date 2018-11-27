/*
 * View model for OctoPrint-Print-Queue
 *
 * Author: Michael New
 * License: AGPLv3
 */

$(function() {
    function PrintQueueViewModel(parameters) {
        var self = this;

        self.printerState = parameters[0];
        self.loginState = parameters[1];
        self.files = parameters[2];

        self.queuedPrints = ko.observableArray([]);
        self.lastId = 0; // used to make each queued entry unique
        self.flatPrintQueue = [];
        self.inhibitSendingQueue = false;

        self.queuedPrints.subscribe(function(changes) {
            if(!self.inhibitSendingQueue) {
                self.checkPrintQueueChanges();
            }
        });

        self.getPrintQueue = function() {
            $.ajax({
                url: "plugin/print_queue/queue",
                type: "GET",
                dataType: "json",
                headers: {
                    "X-Api-Key":UI_API_KEY,
                },
                success: function(data) {
                    self.setPrintQueueFromData(data);
                }
            });
        }
        self.getPrintQueue();


        self.setPrintQueueFromData = function(data) {
            console.log('PQ: received queue');
            self.inhibitSendingQueue = true;
            self.queuedPrints.removeAll();
            self.lastId = 0;
            let lastFileName = undefined;
            for (let i in data.print_queue) {
                fileName = data.print_queue[i];
                if (fileName !== lastFileName) {
                    lastFileName = fileName;
                    self.queuedPrints.push({fileName: fileName, copies: 1, id: self.lastId++});
                } else {
                    let last = self.queuedPrints.pop();
                    last.copies++;
                    self.queuedPrints.push(last);
                }
            }
            self.flatPrintQueue = self.createFlatPrintQueue();
            self.inhibitSendingQueue = false;
        }


        self.createFlatPrintQueue = function() {
            let printList = [];
            for (let i = 0; i < self.queuedPrints().length; i++) {
                let fileName = self.queuedPrints()[i]["fileName"];
                let count = self.queuedPrints()[i]["copies"];
                for (let j = 0; j < count; j++) {
                    printList.push(fileName);
                }
            }
            return printList;
        }


        self.checkPrintQueueChanges = function() {
            console.log('PQ: check queue change');

            let printQueue = self.createFlatPrintQueue();
            if (printQueue != self.flatPrintQueue) {
                self.flatPrintQueue = printQueue;

                $.ajax({
                    url: "plugin/print_queue/queue",
                    type: "POST",
                    dataType: "json",
                    headers: {
                        "X-Api-Key":UI_API_KEY,
                    },
                    data: JSON.stringify(self.createFlatPrintQueue())
                });
            }
        }


        self.startQueue = function() {
            self.clearSelectedFile()
            $.ajax({
                url: "plugin/print_queue/start",
                type: "POST",
                dataType: "json",
                headers: {
                    "X-Api-Key":UI_API_KEY,
                },
                data: JSON.stringify(self.createFlatPrintQueue())
            });
        }

        self.clearQueue = function() {
            self.queuedPrints.removeAll();
        }

        self.moveJobUp = function(data) {
            let currentIndex = self.queuedPrints.indexOf(data);
            if (currentIndex > 0) {
                let queueArray = self.queuedPrints();
                self.queuedPrints.splice(currentIndex-1, 2, queueArray[currentIndex], queueArray[currentIndex - 1]);
            }
        }

        self.moveJobDown = function(data) {
            let currentIndex = self.queuedPrints.indexOf(data);
            if (currentIndex < self.queuedPrints().length - 1) {
                let queueArray = self.queuedPrints();
                self.queuedPrints.splice(currentIndex, 2, queueArray[currentIndex + 1], queueArray[currentIndex]);
            }
        }

        self.removeJob = function(data) {
            self.queuedPrints.remove(data);
        }


        self.clearSelectedFile = function() {
            $.ajax({
                url: "plugin/print_queue/clear_selected_file",
                type: "POST",
                dataType: "json",
                headers: {
                    "X-Api-Key":UI_API_KEY,
                }
            });
            self.files.listHelper.selectNone();
        }

        self.addSelectedFile = function() {
            let f = self.files.listHelper.selectedItem();
            if (f) {
                    self.queuedPrints.push({fileName: f["path"], copies: 1, id: self.lastId++});
                    self.clearSelectedFile();
            } else {
                    self.queuedPrints.push({fileName: "", copies: 1, id: self.lastId++});
            }
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            // if the "add file" field is blank and the user loads a new file
            // put it's name into the text field
            if (plugin != "print_queue") {
                return;
            }

            switch(data["type"]) {
                case "set_queue":
                    self.setPrintQueueFromData(data);
                    break;

                case "file_selected":
                    let accepted = false;
                    for(let i = 0; i < self.queuedPrints().length; i++) {
                        let print = self.queuedPrints()[i];
                        if (print["fileName"] == "") {
                            self.queuedPrints.replace(print, {fileName: data["file"], copies: print["copies"], id: print["id"]})
                            accepted = true;
                        }
                    }
                    if(accepted) {
                        self.clearSelectedFile();
                    }
                    break;
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
        ["printerStateViewModel", "loginStateViewModel", "filesViewModel"],

        // Finally, this is the list of selectors for all elements we want this view model to be bound to.
        ["#tab_plugin_print_queue"]
    ]);
});
