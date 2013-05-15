'use strict';

$(function()
{
    var SPACE = 20;
    var FONT_SIZE = 50;     //changed from 64 

    var svg = d3.select('body')
                .append('svg').attr('id', "textarea")
                .append('g')
                    .attr('transform', 'translate(0, ' + FONT_SIZE + ')')
                .append('text')
                    .attr('font-size', FONT_SIZE);

    
    console.log($("#textarea").width());
    var color = d3.scale.category10(),
        width = d3.scale.linear().range([0, $("#textarea").width()]),
        height = d3.scale.linear().range([0, $("#textarea").height()]);

    var wordID = 0;

    function Word(text)
    {
        if (this)
        {
            this.id = wordID++;
            this.text = text;
        }

        else return new Word(text);
        
    }

    Word.prototype.toString = function ()
    {
        return this.text;
    
    };

    function update(data)
    {
        var words = svg.selectAll('tspan')
                       .data(data, function (d) { return d.id; });

        words.enter().append('tspan')
                     .text(String)
                     .attr('x', width(Math.random()))
                     .attr('y', height(Math.random()))
                     .style('fill', color(Math.random()))   //#0000A0
                     .style('fill-opacity', 0);

        var pos = getWordPositions(words);
        
        
        words.transition()
             .attr('x', function (d, i) { return pos[i].x; })
             .attr('y', function (d, i) { return pos[i].y; })
             .style('fill-opacity', 1);
             
    }

    function getWordPositions(words)
    {
        var pos = [{ x: 0, y: 0 }];

        words.each(function (d, i)
        {
            var len = this.getComputedTextLength() + SPACE;

            if ((pos[0].x + len) > (window.innerWidth - 200) )
            {
                pos[0].x = 0;
                pos[0].y += FONT_SIZE;
            }

            var x = pos[0].x + len;
            var y = pos[0].y;

            pos.unshift({ x: x, y: y });
        });

        pos.shift();

        return pos.reverse();
    }

    var potentials = [""];
    var story = [""];
    update(story);

    var socket = io.connect('/sms');

    socket.on('potential', function (msg){
        //to do
        console.log("potential: " + msg.text);
    });

    socket.on('sms', function (msg)
    {
        //edit so that when we receive an sms to publish, clear the
        //list of potentials
        console.log("sms: " + msg.text);
        var words = msg.text.split(" ").map(Word);

        var end = story.splice(msg.pos);
        story = story.concat(words, end);

        update(story);
    });
});
