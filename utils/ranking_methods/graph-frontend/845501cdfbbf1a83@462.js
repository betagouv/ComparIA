// SPDX-FileCopyrightText: 2023 Lena Jaskov <<https://observablehq.com/@yaslena>
// SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
// SPDX-License-Identifier: MIT

import define1 from "./450051d7f1174df8@254.js";

var storedEncounters = {}

function _1(md){return(
md`# Dynamic Network Graph
`
)}

function _text(md,time){return(
md`Timestamp  of first match  ${time}`
)}

function _time(Scrubber,times){
  return(
Scrubber(times, {
  autoplay: false,
  format: date => date.toLocaleString("fr", { year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',}),
  delay: 400
})
)}

function _chart(d3,width,height,invalidation,colorScale,drag)
{
  const simulation = d3.forceSimulation()
      .force("charge", d3.forceManyBody().strength(-130)) 
      .force("link", d3.forceLink().id(d => d.id).distance(60))
      .force("x", d3.forceX())
      .force("y", d3.forceY())
      .on("tick", ticked);




  const svg = d3.create("svg")
      .attr("viewBox", [-width / 2 - 50, -height / 2 - 50, width + 100, height+100]); 

  let link = svg.append("g")
      .attr("stroke", "#6aadccff")
      .attr("stroke-opacity", 0.3) 
    .selectAll("line");

  let node = svg.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
    .selectAll("circle");

  let text = svg.append("g")
      .attr("font-family", "sans-serif") 
      .attr("font-size", "6px") 
      .selectAll("text");

  function ticked() {
    node.attr("cx", d => d.x)
        .attr("cy", d => d.y);

    link.attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

    text
      .attr("x", d => d.x)
      .attr("y", d => d.y);
  };
    const modelColors = {
                            'X': 'black',     
                            'OpenAI': 'mediumseagreen',
                            'Meta': '#1947d1',
                            'Microsoft': '#00BFFF',
                            'DeepSeek': '#7B68EE',
                            'Mistral AI': '#ffc700',
                            'Alibaba': '#ff9900',
                            'Google':'#ff3d0d',
                            'Anthropic': '#FFCCCC',
                            'jpacifico (individual)':'#FF99CC',
                            'Nvidia': '#FF99CC',
                            '01 AI': '#FF66CC',
                            'AI21 Labs': '#FF6699',
                            'Liquid': '#FF9999',                            
                            'Nous Research': 'lavenderblush',
                            'Cohere': '#CCCCFF',
                            };
    
    const legendData = Object.keys(modelColors).map(modelName => ({
    team: modelName,
    color: modelColors[modelName]}));

    const legend = svg.append("g")
        .attr("class", "legend")
        .attr("transform", `translate(-${width/1.7 }, -${height/3})`);

    const legendItem = legend.selectAll(".legend-item")
        .data(legendData)
        .join("g")
        .attr("class", "legend-item")
        .attr("transform", (d, i) => `translate(0, ${i * 10})`);

    legendItem.append("rect")
    .attr("width", 10)
    .attr("height", 10)
    .attr("fill", d => d.color);

    legendItem.append("text")
    .attr("x", 15)
    .attr("y", 9)
    .text(d => d.team)
    .style("font-size", "6px");

  invalidation.then(() => simulation.stop());

  return Object.assign(svg.node(), {
    update({nodes, links}) {

      console.log(storedEncounters)


      const old = new Map(node.data().map(d => [d.id, d]));
      nodes = nodes.map(d => Object.assign(old.get(d.id) || {}, d));
      links = links.map(d => Object.assign({}, d));

      const maxInDegree = d3.max(nodes, d => d.inDegree) || 1; 
      const radiusScale = d3.scaleLinear()
        .domain([0, maxInDegree])
        .range([1, 20]); 

      const maxLinkWeight = d3.max(links, d => d.weight) || 1;
      
      const linkWidthScale = d3.scaleLinear()
          .domain([1, 20]) // Start domain from 1 for minimum width
          .range([1, 10]); // Range from 1px to 5px for link width

      node = node
        .data(nodes, d => d.id)
        .join(enter => enter.append("circle")
          .attr("r", d => radiusScale(d.inDegree)) 
          .attr("fill","#9467bd") 
          .style("fill", d => modelColors[d.editor])
          .call(drag(simulation))
          .call(node => node.append("title").text(d => `${d.id} (In-Degree: ${d.inDegree})`)), 
          update => update 
            .attr("r", d => radiusScale(d.inDegree)) 
            .call(updateNode => updateNode.select("title").text(d => `${d.id} (In-Degree: ${d.inDegree})`))
            .attr("fill","#9467bd"),
          exit => exit.remove() 
        );
          
      text = text
      .data(nodes, d => d.id) 
      .join(enter => enter.append("text") 
      .attr('class', 'graph-node-labels')
      .style("text-anchor", "middle")
      .style("pointer-events", "none")
      .attr('font-family', 'sans-serif')
      .attr('font-size', '4px') 
      .style("fill", "black") 
      .style("font-weight", "bold")
      .attr('dx', 0)
      .attr('dy', d => 0) 
      .text(d => d.id), 
      update => update 
        .attr('dy', d => 0), 
      exit => exit.remove()
      );


      function sortBubbleWeightForName (dSource, dtarget) {
        return dSource < dtarget ? dSource+dtarget : dtarget+dSource
      }

      function giveWeight(dSource, dtarget) {
        console.log(sortBubbleWeightForName(dSource, dtarget))
        if (storedEncounters[sortBubbleWeightForName(dSource, dtarget)]) {
          storedEncounters[sortBubbleWeightForName(dSource, dtarget)] = storedEncounters[sortBubbleWeightForName(dSource, dtarget)]*5
        } else {
          storedEncounters[sortBubbleWeightForName(dSource, dtarget)] = 1
        }
        return storedEncounters[sortBubbleWeightForName(dSource, dtarget)] / 5
      }

      link = link
        .data(links, d => [d.source, d.target])
        .join("line")
        .attr("stroke-width", d => giveWeight(d.source, d.target));

      simulation.nodes(nodes);
      simulation.force("link").links(links);
      simulation.alpha(1).restart().tick();
      ticked(); 
    }
  });
}

function _update(data,contains,time,chart)
{

  storedEncounters = {}
  const activeLinks = data.links.filter(d => contains(d, time));

  const aggregatedLinksMap = new Map();
  activeLinks.forEach(l => {
      const key = `${l.source}-${l.target}`;
      if (aggregatedLinksMap.has(key)) {
          aggregatedLinksMap.get(key).weight++;
      } else {
          aggregatedLinksMap.set(key, { source: l.source, target: l.target, weight: 1 });
      }
  });
  const aggregatedLinks = Array.from(aggregatedLinksMap.values());


  const originalNodesMap = new Map(data.nodes ? data.nodes.map(n => [n.id, n]) : []);

  const countryIds = new Set();
  activeLinks.forEach(link => {
    countryIds.add(link.source);
    countryIds.add(link.target);
  });

  const nodes = Array.from(countryIds).map(id => {
    const originalNode = originalNodesMap.get(id) || {};
    return {
      id: id,
      inDegree: 0, 
      ...originalNode 
    };
  });


  nodes.forEach(node => {
      node.inDegree = aggregatedLinks.filter(link => link.target === node.id)
                                    .reduce((sum, link) => sum + link.weight, 0);
  });

  chart.update({nodes, links: aggregatedLinks});
}


function _contains(){return(
({start_date, end_date}, time) => start_date <= time && time < end_date
)}

function _7(md){return(
md`# Data`
)}

function _Jsondata(FileAttachment){return(
FileAttachment("treatiesBi@4.json")
)}

async function _data(Jsondata){return(
(await Jsondata).json()
)}

function _10(md){return(
md`# Functions & Definitions`
)}

function _times(data){return(
[...new Set(Array.from(data.links, d  => d.start_date).sort((a, b) => new Date(a).getTime() - new Date(b).getTime() ))]
)}

function _drag(d3){return(
simulation => {
  
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }
  
  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }
  
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }
  
  return d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
}
)}

function _colorScale(d3){return(
d3.scaleOrdinal(d3.schemeSet3)
)}

function _height(){return(
250
)}

function _width(){return(
400
)}

function _16(md){return(
md`# Libraries`
)}

function _d3(require){return(
require("d3@6")
)}

export default function define(runtime, observer) {
  const main = runtime.module();
  function toString() { return this.url; }
  const fileAttachments = new Map([
    ["treatiesBi@4.json", {url: new URL("./files/comparIA_graph.json", import.meta.url), mimeType: "application/json", toString}]
  ]);
  main.builtin("FileAttachment", runtime.fileAttachments(name => fileAttachments.get(name)));
  main.variable(observer("viewof time")).define("viewof time", ["Scrubber","times"], _time);
  main.variable(observer("time")).define("time", ["Generators", "viewof time"], (G, _) => G.input(_));
  main.variable(observer("chart")).define("chart", ["d3","width","height","invalidation","colorScale","drag"], _chart);
  main.variable(observer("update")).define("update", ["data","contains","time","chart"], _update);
  main.variable(observer("contains")).define("contains", _contains);
  main.variable(observer("Jsondata")).define("Jsondata", ["FileAttachment"], _Jsondata);
  main.variable(observer("data")).define("data", ["Jsondata"], _data);
  main.variable(observer("times")).define("times", ["data"], _times);
  main.variable(observer("drag")).define("drag", ["d3"], _drag);
  main.variable(observer("colorScale")).define("colorScale", ["d3"], _colorScale);
  main.variable(observer("height")).define("height", _height);
  main.variable(observer("width")).define("width", _width);
  main.variable(observer("d3")).define("d3", ["require"], _d3);
  const child1 = runtime.module(define1);
  main.import("Scrubber", child1);
  return main;
}
