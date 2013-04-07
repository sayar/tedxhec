'use strict';

window.onload = function ()
{
    var SENTENCE = "The fox jumped over the dog.";

    var SPACE = 20;
    var TIMEOUT = 1000;

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

    function update(data)
    {
        var words = svg.selectAll('tspan')
                       .data(data, String);

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

    var words = SENTENCE.split(" ");

    update(words);

    var edits = [
        { word: "quick", i: 1 },
        { word: "lazy", i: 6 },
        { word: "brown", i: 2 }
    ];

    function edit()
    {
        if (edits.length === 0)
            return;

        var e = edits.shift();

        words.splice(e.i, 0, e.word);
        update(words);

        setTimeout(edit, TIMEOUT);
    }

    setTimeout(edit, TIMEOUT);
};
