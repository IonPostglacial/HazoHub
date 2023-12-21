(function() {
    let hydrated = false;

    function hydrateEditor(editor) {
        if (typeof ClassicEditor === "undefined" || hydrated) return;
        ClassicEditor
            .create(editor)
            .catch(error => {
                console.error( error );
            });
    }
    
    function hydrateRichEditors(elt) {
        const richEditors = Array.from(elt.querySelectorAll(".ckeditor"));
        richEditors.forEach(hydrateEditor);
        hydrated = true;
    }

    function copyNames(e) {
        const names = [
            document.forms.main.nameFR.value,
            document.forms.main.nameEN.value,
            document.forms.main.nameCN.value,
        ];
        navigator.clipboard.writeText(names.join("\t"))
    }

    function onAddEntryKeyPress(event) {
        if (event.key == "Enter") {
            document.getElementById("add-entry").click();
        }
    }

    window.addEventListener("load", function(e) {
        hydrateRichEditors(document);
    });

    window.dict = {
        hydrateRichEditors,
        copyNames,
        onAddEntryKeyPress
    };
}());