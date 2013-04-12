'use strict';

window.onload = function ()
{
    var SERVER_PATH = 'http://localhost:8080/sms';

    var SPACE = 20;
    var FONT_SIZE = 64;

    var svg = d3.select('body')
                .append('svg')
                .append('g')
                    .attr('transform', 'translate(0, ' + FONT_SIZE + ')')
                .append('text')
                    .attr('font-size', FONT_SIZE);

    var color = d3.scale.category10(),
        width = d3.scale.linear().range([0, window.innerWidth]),
        height = d3.scale.linear().range([0, window.innerHeight]);

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
                     .style('fill', color(Math.random()))
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

            if ((pos[0].x + len) > window.innerWidth)
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

    var story = [""];
    update(story);

    var socket = io.connect(SERVER_PATH);

    socket.on('sms', function (msg)
    {
        var words = msg.text.split(" ").map(Word);

        var end = story.splice(msg.pos);
        story = story.concat(words, end);

        update(story);
    });
};
