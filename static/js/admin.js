$(function(){
    var socket = io.connect('/admin');
    var currentDiv;
    socket.on('admin', function(msg){
        $("#smses").append(insertMessageToPage(msg.text, msg.sid))
        if ($("#smses").children().length == 1){
            selectDiv($("#"+msg.sid));
            currentDiv = msg.sid;
        }
    });

    socket.on('admin_remove', function(msg){

        if ($("#smses").children().length == 0){
            currentDiv = null;
            $("#"+msg.sid).remove();
        }
        else{
            selectDiv($("#"+currentDiv).next());
            currentDiv = $("#"+currentDiv).next().attr('id');
            $("#"+msg.sid).remove();
        }
    });

    function insertMessageToPage(text, sid){
        var newdiv = document.createElement('div');
        newdiv.setAttribute('id',sid);
        newdiv.setAttribute('class', 'smstext');
        newdiv.innerHTML = "<div class=\"navbar\">\
                                <div class=\"navbar-inner\">\
                                    <div class=\"container\">\
                                        <ul class=\"nav\"><li><a style=\"font-size: 24px\">" + text + "</a></li></ul>\
                                    </div>\
                                </div>\
                            </div>";
        return newdiv;
    }

    function selectDiv(did){
        did.addClass("navbar-inverse");
    }

    function approveMessage(){
        selectDiv($("#"+currentDiv).next());
        var oldDiv = currentDiv;
        currentDiv = $("#"+currentDiv).next().attr('id');
        socket.emit("approve_sms", { id: $("#"+oldDiv).attr('id'), text: $("#"+oldDiv).find("a").html()});
        $("#"+oldDiv).remove();

    }

    function rejectMessage(){
        selectDiv($("#"+currentDiv).next());
        var oldDiv = currentDiv;
        currentDiv = $("#"+currentDiv).next().attr('id');
        socket.emit("remove_sms", { id: $("#"+oldDiv).attr('id'), text: $("#"+oldDiv).find("a").html()});
        $("#"+oldDiv).remove();
    }

    $(window).keyup(function checkPressedKey(e){
        switch(e.which){
            case 38:
            case 13:
                //enter
                approveMessage()
                break;
            case 32:
                //space
                rejectMessage()
                break;
        }
    });
});
