import{_ as c,ar as U,d as ct,s as me,g as ke,o as ye,p as ge,c as pe,b as ve,v as xe,m as Te,l as bt,j as gt,k as be,e as we,u as _e}from"./mermaid.core-C4JyAOVD.js";import{e as Ft,g as Lt}from"./index-BAPxzJ9I.js";import{t as De,m as Se,a as Ce,i as Ee,b as jt,c as Xt,d as qt,e as Ut,f as Zt,s as Qt,g as Kt,h as Me,j as Ae,k as Ie,l as Fe,n as Le,o as Ye,p as We}from"./time-BmKukK3X.js";import{l as Ve}from"./linear-B6JLprEY.js";import"./step-bAaxMov6.js";import"./svelte/svelte.js";import"./init-Dmth1JHB.js";function Oe(t){return t}var vt=1,St=2,Ct=3,pt=4,$t=1e-6;function ze(t){return"translate("+t+",0)"}function Pe(t){return"translate(0,"+t+")"}function Re(t){return e=>+t(e)}function Ne(t,e){return e=Math.max(0,t.bandwidth()-e*2)/2,t.round()&&(e=Math.round(e)),n=>+t(n)+e}function Be(){return!this.__axis}function re(t,e){var n=[],i=null,a=null,k=6,d=6,D=3,E=typeof window<"u"&&window.devicePixelRatio>1?0:.5,C=t===vt||t===pt?-1:1,g=t===pt||t===St?"x":"y",I=t===vt||t===Ct?ze:Pe;function S(p){var G=i??(e.ticks?e.ticks.apply(e,n):e.domain()),F=a??(e.tickFormat?e.tickFormat.apply(e,n):Oe),v=Math.max(k,0)+D,M=e.range(),L=+M[0]+E,Y=+M[M.length-1]+E,N=(e.bandwidth?Ne:Re)(e.copy(),E),R=p.selection?p.selection():p,j=R.selectAll(".domain").data([null]),z=R.selectAll(".tick").data(G,e).order(),y=z.exit(),b=z.enter().append("g").attr("class","tick"),x=z.select("line"),T=z.select("text");j=j.merge(j.enter().insert("path",".tick").attr("class","domain").attr("stroke","currentColor")),z=z.merge(b),x=x.merge(b.append("line").attr("stroke","currentColor").attr(g+"2",C*k)),T=T.merge(b.append("text").attr("fill","currentColor").attr(g,C*v).attr("dy",t===vt?"0em":t===Ct?"0.71em":"0.32em")),p!==R&&(j=j.transition(p),z=z.transition(p),x=x.transition(p),T=T.transition(p),y=y.transition(p).attr("opacity",$t).attr("transform",function(m){return isFinite(m=N(m))?I(m+E):this.getAttribute("transform")}),b.attr("opacity",$t).attr("transform",function(m){var w=this.parentNode.__axis;return I((w&&isFinite(w=w(m))?w:N(m))+E)})),y.remove(),j.attr("d",t===pt||t===St?d?"M"+C*d+","+L+"H"+E+"V"+Y+"H"+C*d:"M"+E+","+L+"V"+Y:d?"M"+L+","+C*d+"V"+E+"H"+Y+"V"+C*d:"M"+L+","+E+"H"+Y),z.attr("opacity",1).attr("transform",function(m){return I(N(m)+E)}),x.attr(g+"2",C*k),T.attr(g,C*v).text(F),R.filter(Be).attr("fill","none").attr("font-size",10).attr("font-family","sans-serif").attr("text-anchor",t===St?"start":t===pt?"end":"middle"),R.each(function(){this.__axis=N})}return S.scale=function(p){return arguments.length?(e=p,S):e},S.ticks=function(){return n=Array.from(arguments),S},S.tickArguments=function(p){return arguments.length?(n=p==null?[]:Array.from(p),S):n.slice()},S.tickValues=function(p){return arguments.length?(i=p==null?null:Array.from(p),S):i&&i.slice()},S.tickFormat=function(p){return arguments.length?(a=p,S):a},S.tickSize=function(p){return arguments.length?(k=d=+p,S):k},S.tickSizeInner=function(p){return arguments.length?(k=+p,S):k},S.tickSizeOuter=function(p){return arguments.length?(d=+p,S):d},S.tickPadding=function(p){return arguments.length?(D=+p,S):D},S.offset=function(p){return arguments.length?(E=+p,S):E},S}function He(t){return re(vt,t)}function Ge(t){return re(Ct,t)}var ne={exports:{}};(function(t,e){(function(n,i){t.exports=i()})(Ft,function(){var n="day";return function(i,a,k){var d=function(C){return C.add(4-C.isoWeekday(),n)},D=a.prototype;D.isoWeekYear=function(){return d(this).year()},D.isoWeek=function(C){if(!this.$utils().u(C))return this.add(7*(C-this.isoWeek()),n);var g,I,S,p,G=d(this),F=(g=this.isoWeekYear(),I=this.$u,S=(I?k.utc:k)().year(g).startOf("year"),p=4-S.isoWeekday(),S.isoWeekday()>4&&(p+=7),S.add(p,n));return G.diff(F,"week")+1},D.isoWeekday=function(C){return this.$utils().u(C)?this.day()||7:this.day(this.day()%7?C:C-7)};var E=D.startOf;D.startOf=function(C,g){var I=this.$utils(),S=!!I.u(g)||g;return I.p(C)==="isoweek"?S?this.date(this.date()-(this.isoWeekday()-1)).startOf("day"):this.date(this.date()-1-(this.isoWeekday()-1)+7).endOf("day"):E.bind(this)(C,g)}}})})(ne);var je=ne.exports;const Xe=Lt(je);var ie={exports:{}};(function(t,e){(function(n,i){t.exports=i()})(Ft,function(){var n={LTS:"h:mm:ss A",LT:"h:mm A",L:"MM/DD/YYYY",LL:"MMMM D, YYYY",LLL:"MMMM D, YYYY h:mm A",LLLL:"dddd, MMMM D, YYYY h:mm A"},i=/(\[[^[]*\])|([-_:/.,()\s]+)|(A|a|Q|YYYY|YY?|ww?|MM?M?M?|Do|DD?|hh?|HH?|mm?|ss?|S{1,3}|z|ZZ?)/g,a=/\d/,k=/\d\d/,d=/\d\d?/,D=/\d*[^-_:/,()\s\d]+/,E={},C=function(v){return(v=+v)+(v>68?1900:2e3)},g=function(v){return function(M){this[v]=+M}},I=[/[+-]\d\d:?(\d\d)?|Z/,function(v){(this.zone||(this.zone={})).offset=function(M){if(!M||M==="Z")return 0;var L=M.match(/([+-]|\d\d)/g),Y=60*L[1]+(+L[2]||0);return Y===0?0:L[0]==="+"?-Y:Y}(v)}],S=function(v){var M=E[v];return M&&(M.indexOf?M:M.s.concat(M.f))},p=function(v,M){var L,Y=E.meridiem;if(Y){for(var N=1;N<=24;N+=1)if(v.indexOf(Y(N,0,M))>-1){L=N>12;break}}else L=v===(M?"pm":"PM");return L},G={A:[D,function(v){this.afternoon=p(v,!1)}],a:[D,function(v){this.afternoon=p(v,!0)}],Q:[a,function(v){this.month=3*(v-1)+1}],S:[a,function(v){this.milliseconds=100*+v}],SS:[k,function(v){this.milliseconds=10*+v}],SSS:[/\d{3}/,function(v){this.milliseconds=+v}],s:[d,g("seconds")],ss:[d,g("seconds")],m:[d,g("minutes")],mm:[d,g("minutes")],H:[d,g("hours")],h:[d,g("hours")],HH:[d,g("hours")],hh:[d,g("hours")],D:[d,g("day")],DD:[k,g("day")],Do:[D,function(v){var M=E.ordinal,L=v.match(/\d+/);if(this.day=L[0],M)for(var Y=1;Y<=31;Y+=1)M(Y).replace(/\[|\]/g,"")===v&&(this.day=Y)}],w:[d,g("week")],ww:[k,g("week")],M:[d,g("month")],MM:[k,g("month")],MMM:[D,function(v){var M=S("months"),L=(S("monthsShort")||M.map(function(Y){return Y.slice(0,3)})).indexOf(v)+1;if(L<1)throw new Error;this.month=L%12||L}],MMMM:[D,function(v){var M=S("months").indexOf(v)+1;if(M<1)throw new Error;this.month=M%12||M}],Y:[/[+-]?\d+/,g("year")],YY:[k,function(v){this.year=C(v)}],YYYY:[/\d{4}/,g("year")],Z:I,ZZ:I};function F(v){var M,L;M=v,L=E&&E.formats;for(var Y=(v=M.replace(/(\[[^\]]+])|(LTS?|l{1,4}|L{1,4})/g,function(x,T,m){var w=m&&m.toUpperCase();return T||L[m]||n[m]||L[w].replace(/(\[[^\]]+])|(MMMM|MM|DD|dddd)/g,function(o,l,h){return l||h.slice(1)})})).match(i),N=Y.length,R=0;R<N;R+=1){var j=Y[R],z=G[j],y=z&&z[0],b=z&&z[1];Y[R]=b?{regex:y,parser:b}:j.replace(/^\[|\]$/g,"")}return function(x){for(var T={},m=0,w=0;m<N;m+=1){var o=Y[m];if(typeof o=="string")w+=o.length;else{var l=o.regex,h=o.parser,f=x.slice(w),_=l.exec(f)[0];h.call(T,_),x=x.replace(_,"")}}return function(s){var u=s.afternoon;if(u!==void 0){var r=s.hours;u?r<12&&(s.hours+=12):r===12&&(s.hours=0),delete s.afternoon}}(T),T}}return function(v,M,L){L.p.customParseFormat=!0,v&&v.parseTwoDigitYear&&(C=v.parseTwoDigitYear);var Y=M.prototype,N=Y.parse;Y.parse=function(R){var j=R.date,z=R.utc,y=R.args;this.$u=z;var b=y[1];if(typeof b=="string"){var x=y[2]===!0,T=y[3]===!0,m=x||T,w=y[2];T&&(w=y[2]),E=this.$locale(),!x&&w&&(E=L.Ls[w]),this.$d=function(f,_,s,u){try{if(["x","X"].indexOf(_)>-1)return new Date((_==="X"?1e3:1)*f);var r=F(_)(f),W=r.year,A=r.month,V=r.day,X=r.hours,O=r.minutes,P=r.seconds,K=r.milliseconds,st=r.zone,at=r.week,dt=new Date,ft=V||(W||A?1:dt.getDate()),ot=W||dt.getFullYear(),B=0;W&&!A||(B=A>0?A-1:dt.getMonth());var Q,q=X||0,nt=O||0,$=P||0,rt=K||0;return st?new Date(Date.UTC(ot,B,ft,q,nt,$,rt+60*st.offset*1e3)):s?new Date(Date.UTC(ot,B,ft,q,nt,$,rt)):(Q=new Date(ot,B,ft,q,nt,$,rt),at&&(Q=u(Q).week(at).toDate()),Q)}catch{return new Date("")}}(j,b,z,L),this.init(),w&&w!==!0&&(this.$L=this.locale(w).$L),m&&j!=this.format(b)&&(this.$d=new Date("")),E={}}else if(b instanceof Array)for(var o=b.length,l=1;l<=o;l+=1){y[1]=b[l-1];var h=L.apply(this,y);if(h.isValid()){this.$d=h.$d,this.$L=h.$L,this.init();break}l===o&&(this.$d=new Date(""))}else N.call(this,R)}}})})(ie);var qe=ie.exports;const Ue=Lt(qe);var se={exports:{}};(function(t,e){(function(n,i){t.exports=i()})(Ft,function(){return function(n,i){var a=i.prototype,k=a.format;a.format=function(d){var D=this,E=this.$locale();if(!this.isValid())return k.bind(this)(d);var C=this.$utils(),g=(d||"YYYY-MM-DDTHH:mm:ssZ").replace(/\[([^\]]+)]|Q|wo|ww|w|WW|W|zzz|z|gggg|GGGG|Do|X|x|k{1,2}|S/g,function(I){switch(I){case"Q":return Math.ceil((D.$M+1)/3);case"Do":return E.ordinal(D.$D);case"gggg":return D.weekYear();case"GGGG":return D.isoWeekYear();case"wo":return E.ordinal(D.week(),"W");case"w":case"ww":return C.s(D.week(),I==="w"?1:2,"0");case"W":case"WW":return C.s(D.isoWeek(),I==="W"?1:2,"0");case"k":case"kk":return C.s(String(D.$H===0?24:D.$H),I==="k"?1:2,"0");case"X":return Math.floor(D.$d.getTime()/1e3);case"x":return D.$d.getTime();case"z":return"["+D.offsetName()+"]";case"zzz":return"["+D.offsetName("long")+"]";default:return I}});return k.bind(this)(g)}}})})(se);var Ze=se.exports;const Qe=Lt(Ze);var Et=function(){var t=c(function(w,o,l,h){for(l=l||{},h=w.length;h--;l[w[h]]=o);return l},"o"),e=[6,8,10,12,13,14,15,16,17,18,20,21,22,23,24,25,26,27,28,29,30,31,33,35,36,38,40],n=[1,26],i=[1,27],a=[1,28],k=[1,29],d=[1,30],D=[1,31],E=[1,32],C=[1,33],g=[1,34],I=[1,9],S=[1,10],p=[1,11],G=[1,12],F=[1,13],v=[1,14],M=[1,15],L=[1,16],Y=[1,19],N=[1,20],R=[1,21],j=[1,22],z=[1,23],y=[1,25],b=[1,35],x={trace:c(function(){},"trace"),yy:{},symbols_:{error:2,start:3,gantt:4,document:5,EOF:6,line:7,SPACE:8,statement:9,NL:10,weekday:11,weekday_monday:12,weekday_tuesday:13,weekday_wednesday:14,weekday_thursday:15,weekday_friday:16,weekday_saturday:17,weekday_sunday:18,weekend:19,weekend_friday:20,weekend_saturday:21,dateFormat:22,inclusiveEndDates:23,topAxis:24,axisFormat:25,tickInterval:26,excludes:27,includes:28,todayMarker:29,title:30,acc_title:31,acc_title_value:32,acc_descr:33,acc_descr_value:34,acc_descr_multiline_value:35,section:36,clickStatement:37,taskTxt:38,taskData:39,click:40,callbackname:41,callbackargs:42,href:43,clickStatementDebug:44,$accept:0,$end:1},terminals_:{2:"error",4:"gantt",6:"EOF",8:"SPACE",10:"NL",12:"weekday_monday",13:"weekday_tuesday",14:"weekday_wednesday",15:"weekday_thursday",16:"weekday_friday",17:"weekday_saturday",18:"weekday_sunday",20:"weekend_friday",21:"weekend_saturday",22:"dateFormat",23:"inclusiveEndDates",24:"topAxis",25:"axisFormat",26:"tickInterval",27:"excludes",28:"includes",29:"todayMarker",30:"title",31:"acc_title",32:"acc_title_value",33:"acc_descr",34:"acc_descr_value",35:"acc_descr_multiline_value",36:"section",38:"taskTxt",39:"taskData",40:"click",41:"callbackname",42:"callbackargs",43:"href"},productions_:[0,[3,3],[5,0],[5,2],[7,2],[7,1],[7,1],[7,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[19,1],[19,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,2],[9,2],[9,1],[9,1],[9,1],[9,2],[37,2],[37,3],[37,3],[37,4],[37,3],[37,4],[37,2],[44,2],[44,3],[44,3],[44,4],[44,3],[44,4],[44,2]],performAction:c(function(o,l,h,f,_,s,u){var r=s.length-1;switch(_){case 1:return s[r-1];case 2:this.$=[];break;case 3:s[r-1].push(s[r]),this.$=s[r-1];break;case 4:case 5:this.$=s[r];break;case 6:case 7:this.$=[];break;case 8:f.setWeekday("monday");break;case 9:f.setWeekday("tuesday");break;case 10:f.setWeekday("wednesday");break;case 11:f.setWeekday("thursday");break;case 12:f.setWeekday("friday");break;case 13:f.setWeekday("saturday");break;case 14:f.setWeekday("sunday");break;case 15:f.setWeekend("friday");break;case 16:f.setWeekend("saturday");break;case 17:f.setDateFormat(s[r].substr(11)),this.$=s[r].substr(11);break;case 18:f.enableInclusiveEndDates(),this.$=s[r].substr(18);break;case 19:f.TopAxis(),this.$=s[r].substr(8);break;case 20:f.setAxisFormat(s[r].substr(11)),this.$=s[r].substr(11);break;case 21:f.setTickInterval(s[r].substr(13)),this.$=s[r].substr(13);break;case 22:f.setExcludes(s[r].substr(9)),this.$=s[r].substr(9);break;case 23:f.setIncludes(s[r].substr(9)),this.$=s[r].substr(9);break;case 24:f.setTodayMarker(s[r].substr(12)),this.$=s[r].substr(12);break;case 27:f.setDiagramTitle(s[r].substr(6)),this.$=s[r].substr(6);break;case 28:this.$=s[r].trim(),f.setAccTitle(this.$);break;case 29:case 30:this.$=s[r].trim(),f.setAccDescription(this.$);break;case 31:f.addSection(s[r].substr(8)),this.$=s[r].substr(8);break;case 33:f.addTask(s[r-1],s[r]),this.$="task";break;case 34:this.$=s[r-1],f.setClickEvent(s[r-1],s[r],null);break;case 35:this.$=s[r-2],f.setClickEvent(s[r-2],s[r-1],s[r]);break;case 36:this.$=s[r-2],f.setClickEvent(s[r-2],s[r-1],null),f.setLink(s[r-2],s[r]);break;case 37:this.$=s[r-3],f.setClickEvent(s[r-3],s[r-2],s[r-1]),f.setLink(s[r-3],s[r]);break;case 38:this.$=s[r-2],f.setClickEvent(s[r-2],s[r],null),f.setLink(s[r-2],s[r-1]);break;case 39:this.$=s[r-3],f.setClickEvent(s[r-3],s[r-1],s[r]),f.setLink(s[r-3],s[r-2]);break;case 40:this.$=s[r-1],f.setLink(s[r-1],s[r]);break;case 41:case 47:this.$=s[r-1]+" "+s[r];break;case 42:case 43:case 45:this.$=s[r-2]+" "+s[r-1]+" "+s[r];break;case 44:case 46:this.$=s[r-3]+" "+s[r-2]+" "+s[r-1]+" "+s[r];break}},"anonymous"),table:[{3:1,4:[1,2]},{1:[3]},t(e,[2,2],{5:3}),{6:[1,4],7:5,8:[1,6],9:7,10:[1,8],11:17,12:n,13:i,14:a,15:k,16:d,17:D,18:E,19:18,20:C,21:g,22:I,23:S,24:p,25:G,26:F,27:v,28:M,29:L,30:Y,31:N,33:R,35:j,36:z,37:24,38:y,40:b},t(e,[2,7],{1:[2,1]}),t(e,[2,3]),{9:36,11:17,12:n,13:i,14:a,15:k,16:d,17:D,18:E,19:18,20:C,21:g,22:I,23:S,24:p,25:G,26:F,27:v,28:M,29:L,30:Y,31:N,33:R,35:j,36:z,37:24,38:y,40:b},t(e,[2,5]),t(e,[2,6]),t(e,[2,17]),t(e,[2,18]),t(e,[2,19]),t(e,[2,20]),t(e,[2,21]),t(e,[2,22]),t(e,[2,23]),t(e,[2,24]),t(e,[2,25]),t(e,[2,26]),t(e,[2,27]),{32:[1,37]},{34:[1,38]},t(e,[2,30]),t(e,[2,31]),t(e,[2,32]),{39:[1,39]},t(e,[2,8]),t(e,[2,9]),t(e,[2,10]),t(e,[2,11]),t(e,[2,12]),t(e,[2,13]),t(e,[2,14]),t(e,[2,15]),t(e,[2,16]),{41:[1,40],43:[1,41]},t(e,[2,4]),t(e,[2,28]),t(e,[2,29]),t(e,[2,33]),t(e,[2,34],{42:[1,42],43:[1,43]}),t(e,[2,40],{41:[1,44]}),t(e,[2,35],{43:[1,45]}),t(e,[2,36]),t(e,[2,38],{42:[1,46]}),t(e,[2,37]),t(e,[2,39])],defaultActions:{},parseError:c(function(o,l){if(l.recoverable)this.trace(o);else{var h=new Error(o);throw h.hash=l,h}},"parseError"),parse:c(function(o){var l=this,h=[0],f=[],_=[null],s=[],u=this.table,r="",W=0,A=0,V=2,X=1,O=s.slice.call(arguments,1),P=Object.create(this.lexer),K={yy:{}};for(var st in this.yy)Object.prototype.hasOwnProperty.call(this.yy,st)&&(K.yy[st]=this.yy[st]);P.setInput(o,K.yy),K.yy.lexer=P,K.yy.parser=this,typeof P.yylloc>"u"&&(P.yylloc={});var at=P.yylloc;s.push(at);var dt=P.options&&P.options.ranges;typeof K.yy.parseError=="function"?this.parseError=K.yy.parseError:this.parseError=Object.getPrototypeOf(this).parseError;function ft(Z){h.length=h.length-2*Z,_.length=_.length-Z,s.length=s.length-Z}c(ft,"popStack");function ot(){var Z;return Z=f.pop()||P.lex()||X,typeof Z!="number"&&(Z instanceof Array&&(f=Z,Z=f.pop()),Z=l.symbols_[Z]||Z),Z}c(ot,"lex");for(var B,Q,q,nt,$={},rt,J,Gt,yt;;){if(Q=h[h.length-1],this.defaultActions[Q]?q=this.defaultActions[Q]:((B===null||typeof B>"u")&&(B=ot()),q=u[Q]&&u[Q][B]),typeof q>"u"||!q.length||!q[0]){var Dt="";yt=[];for(rt in u[Q])this.terminals_[rt]&&rt>V&&yt.push("'"+this.terminals_[rt]+"'");P.showPosition?Dt="Parse error on line "+(W+1)+`:
`+P.showPosition()+`
Expecting `+yt.join(", ")+", got '"+(this.terminals_[B]||B)+"'":Dt="Parse error on line "+(W+1)+": Unexpected "+(B==X?"end of input":"'"+(this.terminals_[B]||B)+"'"),this.parseError(Dt,{text:P.match,token:this.terminals_[B]||B,line:P.yylineno,loc:at,expected:yt})}if(q[0]instanceof Array&&q.length>1)throw new Error("Parse Error: multiple actions possible at state: "+Q+", token: "+B);switch(q[0]){case 1:h.push(B),_.push(P.yytext),s.push(P.yylloc),h.push(q[1]),B=null,A=P.yyleng,r=P.yytext,W=P.yylineno,at=P.yylloc;break;case 2:if(J=this.productions_[q[1]][1],$.$=_[_.length-J],$._$={first_line:s[s.length-(J||1)].first_line,last_line:s[s.length-1].last_line,first_column:s[s.length-(J||1)].first_column,last_column:s[s.length-1].last_column},dt&&($._$.range=[s[s.length-(J||1)].range[0],s[s.length-1].range[1]]),nt=this.performAction.apply($,[r,A,W,K.yy,q[1],_,s].concat(O)),typeof nt<"u")return nt;J&&(h=h.slice(0,-1*J*2),_=_.slice(0,-1*J),s=s.slice(0,-1*J)),h.push(this.productions_[q[1]][0]),_.push($.$),s.push($._$),Gt=u[h[h.length-2]][h[h.length-1]],h.push(Gt);break;case 3:return!0}}return!0},"parse")},T=function(){var w={EOF:1,parseError:c(function(l,h){if(this.yy.parser)this.yy.parser.parseError(l,h);else throw new Error(l)},"parseError"),setInput:c(function(o,l){return this.yy=l||this.yy||{},this._input=o,this._more=this._backtrack=this.done=!1,this.yylineno=this.yyleng=0,this.yytext=this.matched=this.match="",this.conditionStack=["INITIAL"],this.yylloc={first_line:1,first_column:0,last_line:1,last_column:0},this.options.ranges&&(this.yylloc.range=[0,0]),this.offset=0,this},"setInput"),input:c(function(){var o=this._input[0];this.yytext+=o,this.yyleng++,this.offset++,this.match+=o,this.matched+=o;var l=o.match(/(?:\r\n?|\n).*/g);return l?(this.yylineno++,this.yylloc.last_line++):this.yylloc.last_column++,this.options.ranges&&this.yylloc.range[1]++,this._input=this._input.slice(1),o},"input"),unput:c(function(o){var l=o.length,h=o.split(/(?:\r\n?|\n)/g);this._input=o+this._input,this.yytext=this.yytext.substr(0,this.yytext.length-l),this.offset-=l;var f=this.match.split(/(?:\r\n?|\n)/g);this.match=this.match.substr(0,this.match.length-1),this.matched=this.matched.substr(0,this.matched.length-1),h.length-1&&(this.yylineno-=h.length-1);var _=this.yylloc.range;return this.yylloc={first_line:this.yylloc.first_line,last_line:this.yylineno+1,first_column:this.yylloc.first_column,last_column:h?(h.length===f.length?this.yylloc.first_column:0)+f[f.length-h.length].length-h[0].length:this.yylloc.first_column-l},this.options.ranges&&(this.yylloc.range=[_[0],_[0]+this.yyleng-l]),this.yyleng=this.yytext.length,this},"unput"),more:c(function(){return this._more=!0,this},"more"),reject:c(function(){if(this.options.backtrack_lexer)this._backtrack=!0;else return this.parseError("Lexical error on line "+(this.yylineno+1)+`. You can only invoke reject() in the lexer when the lexer is of the backtracking persuasion (options.backtrack_lexer = true).
`+this.showPosition(),{text:"",token:null,line:this.yylineno});return this},"reject"),less:c(function(o){this.unput(this.match.slice(o))},"less"),pastInput:c(function(){var o=this.matched.substr(0,this.matched.length-this.match.length);return(o.length>20?"...":"")+o.substr(-20).replace(/\n/g,"")},"pastInput"),upcomingInput:c(function(){var o=this.match;return o.length<20&&(o+=this._input.substr(0,20-o.length)),(o.substr(0,20)+(o.length>20?"...":"")).replace(/\n/g,"")},"upcomingInput"),showPosition:c(function(){var o=this.pastInput(),l=new Array(o.length+1).join("-");return o+this.upcomingInput()+`
`+l+"^"},"showPosition"),test_match:c(function(o,l){var h,f,_;if(this.options.backtrack_lexer&&(_={yylineno:this.yylineno,yylloc:{first_line:this.yylloc.first_line,last_line:this.last_line,first_column:this.yylloc.first_column,last_column:this.yylloc.last_column},yytext:this.yytext,match:this.match,matches:this.matches,matched:this.matched,yyleng:this.yyleng,offset:this.offset,_more:this._more,_input:this._input,yy:this.yy,conditionStack:this.conditionStack.slice(0),done:this.done},this.options.ranges&&(_.yylloc.range=this.yylloc.range.slice(0))),f=o[0].match(/(?:\r\n?|\n).*/g),f&&(this.yylineno+=f.length),this.yylloc={first_line:this.yylloc.last_line,last_line:this.yylineno+1,first_column:this.yylloc.last_column,last_column:f?f[f.length-1].length-f[f.length-1].match(/\r?\n?/)[0].length:this.yylloc.last_column+o[0].length},this.yytext+=o[0],this.match+=o[0],this.matches=o,this.yyleng=this.yytext.length,this.options.ranges&&(this.yylloc.range=[this.offset,this.offset+=this.yyleng]),this._more=!1,this._backtrack=!1,this._input=this._input.slice(o[0].length),this.matched+=o[0],h=this.performAction.call(this,this.yy,this,l,this.conditionStack[this.conditionStack.length-1]),this.done&&this._input&&(this.done=!1),h)return h;if(this._backtrack){for(var s in _)this[s]=_[s];return!1}return!1},"test_match"),next:c(function(){if(this.done)return this.EOF;this._input||(this.done=!0);var o,l,h,f;this._more||(this.yytext="",this.match="");for(var _=this._currentRules(),s=0;s<_.length;s++)if(h=this._input.match(this.rules[_[s]]),h&&(!l||h[0].length>l[0].length)){if(l=h,f=s,this.options.backtrack_lexer){if(o=this.test_match(h,_[s]),o!==!1)return o;if(this._backtrack){l=!1;continue}else return!1}else if(!this.options.flex)break}return l?(o=this.test_match(l,_[f]),o!==!1?o:!1):this._input===""?this.EOF:this.parseError("Lexical error on line "+(this.yylineno+1)+`. Unrecognized text.
`+this.showPosition(),{text:"",token:null,line:this.yylineno})},"next"),lex:c(function(){var l=this.next();return l||this.lex()},"lex"),begin:c(function(l){this.conditionStack.push(l)},"begin"),popState:c(function(){var l=this.conditionStack.length-1;return l>0?this.conditionStack.pop():this.conditionStack[0]},"popState"),_currentRules:c(function(){return this.conditionStack.length&&this.conditionStack[this.conditionStack.length-1]?this.conditions[this.conditionStack[this.conditionStack.length-1]].rules:this.conditions.INITIAL.rules},"_currentRules"),topState:c(function(l){return l=this.conditionStack.length-1-Math.abs(l||0),l>=0?this.conditionStack[l]:"INITIAL"},"topState"),pushState:c(function(l){this.begin(l)},"pushState"),stateStackSize:c(function(){return this.conditionStack.length},"stateStackSize"),options:{"case-insensitive":!0},performAction:c(function(l,h,f,_){switch(f){case 0:return this.begin("open_directive"),"open_directive";case 1:return this.begin("acc_title"),31;case 2:return this.popState(),"acc_title_value";case 3:return this.begin("acc_descr"),33;case 4:return this.popState(),"acc_descr_value";case 5:this.begin("acc_descr_multiline");break;case 6:this.popState();break;case 7:return"acc_descr_multiline_value";case 8:break;case 9:break;case 10:break;case 11:return 10;case 12:break;case 13:break;case 14:this.begin("href");break;case 15:this.popState();break;case 16:return 43;case 17:this.begin("callbackname");break;case 18:this.popState();break;case 19:this.popState(),this.begin("callbackargs");break;case 20:return 41;case 21:this.popState();break;case 22:return 42;case 23:this.begin("click");break;case 24:this.popState();break;case 25:return 40;case 26:return 4;case 27:return 22;case 28:return 23;case 29:return 24;case 30:return 25;case 31:return 26;case 32:return 28;case 33:return 27;case 34:return 29;case 35:return 12;case 36:return 13;case 37:return 14;case 38:return 15;case 39:return 16;case 40:return 17;case 41:return 18;case 42:return 20;case 43:return 21;case 44:return"date";case 45:return 30;case 46:return"accDescription";case 47:return 36;case 48:return 38;case 49:return 39;case 50:return":";case 51:return 6;case 52:return"INVALID"}},"anonymous"),rules:[/^(?:%%\{)/i,/^(?:accTitle\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*\{\s*)/i,/^(?:[\}])/i,/^(?:[^\}]*)/i,/^(?:%%(?!\{)*[^\n]*)/i,/^(?:[^\}]%%*[^\n]*)/i,/^(?:%%*[^\n]*[\n]*)/i,/^(?:[\n]+)/i,/^(?:\s+)/i,/^(?:%[^\n]*)/i,/^(?:href[\s]+["])/i,/^(?:["])/i,/^(?:[^"]*)/i,/^(?:call[\s]+)/i,/^(?:\([\s]*\))/i,/^(?:\()/i,/^(?:[^(]*)/i,/^(?:\))/i,/^(?:[^)]*)/i,/^(?:click[\s]+)/i,/^(?:[\s\n])/i,/^(?:[^\s\n]*)/i,/^(?:gantt\b)/i,/^(?:dateFormat\s[^#\n;]+)/i,/^(?:inclusiveEndDates\b)/i,/^(?:topAxis\b)/i,/^(?:axisFormat\s[^#\n;]+)/i,/^(?:tickInterval\s[^#\n;]+)/i,/^(?:includes\s[^#\n;]+)/i,/^(?:excludes\s[^#\n;]+)/i,/^(?:todayMarker\s[^\n;]+)/i,/^(?:weekday\s+monday\b)/i,/^(?:weekday\s+tuesday\b)/i,/^(?:weekday\s+wednesday\b)/i,/^(?:weekday\s+thursday\b)/i,/^(?:weekday\s+friday\b)/i,/^(?:weekday\s+saturday\b)/i,/^(?:weekday\s+sunday\b)/i,/^(?:weekend\s+friday\b)/i,/^(?:weekend\s+saturday\b)/i,/^(?:\d\d\d\d-\d\d-\d\d\b)/i,/^(?:title\s[^\n]+)/i,/^(?:accDescription\s[^#\n;]+)/i,/^(?:section\s[^\n]+)/i,/^(?:[^:\n]+)/i,/^(?::[^#\n;]+)/i,/^(?::)/i,/^(?:$)/i,/^(?:.)/i],conditions:{acc_descr_multiline:{rules:[6,7],inclusive:!1},acc_descr:{rules:[4],inclusive:!1},acc_title:{rules:[2],inclusive:!1},callbackargs:{rules:[21,22],inclusive:!1},callbackname:{rules:[18,19,20],inclusive:!1},href:{rules:[15,16],inclusive:!1},click:{rules:[24,25],inclusive:!1},INITIAL:{rules:[0,1,3,5,8,9,10,11,12,13,14,17,23,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52],inclusive:!0}}};return w}();x.lexer=T;function m(){this.yy={}}return c(m,"Parser"),m.prototype=x,x.Parser=m,new m}();Et.parser=Et;var Ke=Et;U.extend(Xe);U.extend(Ue);U.extend(Qe);var Jt={friday:5,saturday:6},tt="",Yt="",Wt=void 0,Vt="",ht=[],mt=[],Ot=new Map,zt=[],wt=[],ut="",Pt="",ae=["active","done","crit","milestone"],Rt=[],kt=!1,Nt=!1,Bt="sunday",_t="saturday",Mt=0,$e=c(function(){zt=[],wt=[],ut="",Rt=[],xt=0,It=void 0,Tt=void 0,H=[],tt="",Yt="",Pt="",Wt=void 0,Vt="",ht=[],mt=[],kt=!1,Nt=!1,Mt=0,Ot=new Map,xe(),Bt="sunday",_t="saturday"},"clear"),Je=c(function(t){Yt=t},"setAxisFormat"),tr=c(function(){return Yt},"getAxisFormat"),er=c(function(t){Wt=t},"setTickInterval"),rr=c(function(){return Wt},"getTickInterval"),nr=c(function(t){Vt=t},"setTodayMarker"),ir=c(function(){return Vt},"getTodayMarker"),sr=c(function(t){tt=t},"setDateFormat"),ar=c(function(){kt=!0},"enableInclusiveEndDates"),or=c(function(){return kt},"endDatesAreInclusive"),cr=c(function(){Nt=!0},"enableTopAxis"),lr=c(function(){return Nt},"topAxisEnabled"),ur=c(function(t){Pt=t},"setDisplayMode"),dr=c(function(){return Pt},"getDisplayMode"),fr=c(function(){return tt},"getDateFormat"),hr=c(function(t){ht=t.toLowerCase().split(/[\s,]+/)},"setIncludes"),mr=c(function(){return ht},"getIncludes"),kr=c(function(t){mt=t.toLowerCase().split(/[\s,]+/)},"setExcludes"),yr=c(function(){return mt},"getExcludes"),gr=c(function(){return Ot},"getLinks"),pr=c(function(t){ut=t,zt.push(t)},"addSection"),vr=c(function(){return zt},"getSections"),xr=c(function(){let t=te();const e=10;let n=0;for(;!t&&n<e;)t=te(),n++;return wt=H,wt},"getTasks"),oe=c(function(t,e,n,i){return i.includes(t.format(e.trim()))?!1:n.includes("weekends")&&(t.isoWeekday()===Jt[_t]||t.isoWeekday()===Jt[_t]+1)||n.includes(t.format("dddd").toLowerCase())?!0:n.includes(t.format(e.trim()))},"isInvalidDate"),Tr=c(function(t){Bt=t},"setWeekday"),br=c(function(){return Bt},"getWeekday"),wr=c(function(t){_t=t},"setWeekend"),ce=c(function(t,e,n,i){if(!n.length||t.manualEndTime)return;let a;t.startTime instanceof Date?a=U(t.startTime):a=U(t.startTime,e,!0),a=a.add(1,"d");let k;t.endTime instanceof Date?k=U(t.endTime):k=U(t.endTime,e,!0);const[d,D]=_r(a,k,e,n,i);t.endTime=d.toDate(),t.renderEndTime=D},"checkTaskDates"),_r=c(function(t,e,n,i,a){let k=!1,d=null;for(;t<=e;)k||(d=e.toDate()),k=oe(t,n,i,a),k&&(e=e.add(1,"d")),t=t.add(1,"d");return[e,d]},"fixTaskDates"),At=c(function(t,e,n){n=n.trim();const a=/^after\s+(?<ids>[\d\w- ]+)/.exec(n);if(a!==null){let d=null;for(const E of a.groups.ids.split(" ")){let C=it(E);C!==void 0&&(!d||C.endTime>d.endTime)&&(d=C)}if(d)return d.endTime;const D=new Date;return D.setHours(0,0,0,0),D}let k=U(n,e.trim(),!0);if(k.isValid())return k.toDate();{bt.debug("Invalid date:"+n),bt.debug("With date format:"+e.trim());const d=new Date(n);if(d===void 0||isNaN(d.getTime())||d.getFullYear()<-1e4||d.getFullYear()>1e4)throw new Error("Invalid date:"+n);return d}},"getStartDate"),le=c(function(t){const e=/^(\d+(?:\.\d+)?)([Mdhmswy]|ms)$/.exec(t.trim());return e!==null?[Number.parseFloat(e[1]),e[2]]:[NaN,"ms"]},"parseDuration"),ue=c(function(t,e,n,i=!1){n=n.trim();const k=/^until\s+(?<ids>[\d\w- ]+)/.exec(n);if(k!==null){let g=null;for(const S of k.groups.ids.split(" ")){let p=it(S);p!==void 0&&(!g||p.startTime<g.startTime)&&(g=p)}if(g)return g.startTime;const I=new Date;return I.setHours(0,0,0,0),I}let d=U(n,e.trim(),!0);if(d.isValid())return i&&(d=d.add(1,"d")),d.toDate();let D=U(t);const[E,C]=le(n);if(!Number.isNaN(E)){const g=D.add(E,C);g.isValid()&&(D=g)}return D.toDate()},"getEndDate"),xt=0,lt=c(function(t){return t===void 0?(xt=xt+1,"task"+xt):t},"parseId"),Dr=c(function(t,e){let n;e.substr(0,1)===":"?n=e.substr(1,e.length):n=e;const i=n.split(","),a={};Ht(i,a,ae);for(let d=0;d<i.length;d++)i[d]=i[d].trim();let k="";switch(i.length){case 1:a.id=lt(),a.startTime=t.endTime,k=i[0];break;case 2:a.id=lt(),a.startTime=At(void 0,tt,i[0]),k=i[1];break;case 3:a.id=lt(i[0]),a.startTime=At(void 0,tt,i[1]),k=i[2];break}return k&&(a.endTime=ue(a.startTime,tt,k,kt),a.manualEndTime=U(k,"YYYY-MM-DD",!0).isValid(),ce(a,tt,mt,ht)),a},"compileData"),Sr=c(function(t,e){let n;e.substr(0,1)===":"?n=e.substr(1,e.length):n=e;const i=n.split(","),a={};Ht(i,a,ae);for(let k=0;k<i.length;k++)i[k]=i[k].trim();switch(i.length){case 1:a.id=lt(),a.startTime={type:"prevTaskEnd",id:t},a.endTime={data:i[0]};break;case 2:a.id=lt(),a.startTime={type:"getStartDate",startData:i[0]},a.endTime={data:i[1]};break;case 3:a.id=lt(i[0]),a.startTime={type:"getStartDate",startData:i[1]},a.endTime={data:i[2]};break}return a},"parseData"),It,Tt,H=[],de={},Cr=c(function(t,e){const n={section:ut,type:ut,processed:!1,manualEndTime:!1,renderEndTime:null,raw:{data:e},task:t,classes:[]},i=Sr(Tt,e);n.raw.startTime=i.startTime,n.raw.endTime=i.endTime,n.id=i.id,n.prevTaskId=Tt,n.active=i.active,n.done=i.done,n.crit=i.crit,n.milestone=i.milestone,n.order=Mt,Mt++;const a=H.push(n);Tt=n.id,de[n.id]=a-1},"addTask"),it=c(function(t){const e=de[t];return H[e]},"findTaskById"),Er=c(function(t,e){const n={section:ut,type:ut,description:t,task:t,classes:[]},i=Dr(It,e);n.startTime=i.startTime,n.endTime=i.endTime,n.id=i.id,n.active=i.active,n.done=i.done,n.crit=i.crit,n.milestone=i.milestone,It=n,wt.push(n)},"addTaskOrg"),te=c(function(){const t=c(function(n){const i=H[n];let a="";switch(H[n].raw.startTime.type){case"prevTaskEnd":{const k=it(i.prevTaskId);i.startTime=k.endTime;break}case"getStartDate":a=At(void 0,tt,H[n].raw.startTime.startData),a&&(H[n].startTime=a);break}return H[n].startTime&&(H[n].endTime=ue(H[n].startTime,tt,H[n].raw.endTime.data,kt),H[n].endTime&&(H[n].processed=!0,H[n].manualEndTime=U(H[n].raw.endTime.data,"YYYY-MM-DD",!0).isValid(),ce(H[n],tt,mt,ht))),H[n].processed},"compileTask");let e=!0;for(const[n,i]of H.entries())t(n),e=e&&i.processed;return e},"compileTasks"),Mr=c(function(t,e){let n=e;ct().securityLevel!=="loose"&&(n=Te(e)),t.split(",").forEach(function(i){it(i)!==void 0&&(he(i,()=>{window.open(n,"_self")}),Ot.set(i,n))}),fe(t,"clickable")},"setLink"),fe=c(function(t,e){t.split(",").forEach(function(n){let i=it(n);i!==void 0&&i.classes.push(e)})},"setClass"),Ar=c(function(t,e,n){if(ct().securityLevel!=="loose"||e===void 0)return;let i=[];if(typeof n=="string"){i=n.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);for(let k=0;k<i.length;k++){let d=i[k].trim();d.startsWith('"')&&d.endsWith('"')&&(d=d.substr(1,d.length-2)),i[k]=d}}i.length===0&&i.push(t),it(t)!==void 0&&he(t,()=>{_e.runFunc(e,...i)})},"setClickFun"),he=c(function(t,e){Rt.push(function(){const n=document.querySelector(`[id="${t}"]`);n!==null&&n.addEventListener("click",function(){e()})},function(){const n=document.querySelector(`[id="${t}-text"]`);n!==null&&n.addEventListener("click",function(){e()})})},"pushFun"),Ir=c(function(t,e,n){t.split(",").forEach(function(i){Ar(i,e,n)}),fe(t,"clickable")},"setClickEvent"),Fr=c(function(t){Rt.forEach(function(e){e(t)})},"bindFunctions"),Lr={getConfig:c(()=>ct().gantt,"getConfig"),clear:$e,setDateFormat:sr,getDateFormat:fr,enableInclusiveEndDates:ar,endDatesAreInclusive:or,enableTopAxis:cr,topAxisEnabled:lr,setAxisFormat:Je,getAxisFormat:tr,setTickInterval:er,getTickInterval:rr,setTodayMarker:nr,getTodayMarker:ir,setAccTitle:me,getAccTitle:ke,setDiagramTitle:ye,getDiagramTitle:ge,setDisplayMode:ur,getDisplayMode:dr,setAccDescription:pe,getAccDescription:ve,addSection:pr,getSections:vr,getTasks:xr,addTask:Cr,findTaskById:it,addTaskOrg:Er,setIncludes:hr,getIncludes:mr,setExcludes:kr,getExcludes:yr,setClickEvent:Ir,setLink:Mr,getLinks:gr,bindFunctions:Fr,parseDuration:le,isInvalidDate:oe,setWeekday:Tr,getWeekday:br,setWeekend:wr};function Ht(t,e,n){let i=!0;for(;i;)i=!1,n.forEach(function(a){const k="^\\s*"+a+"\\s*$",d=new RegExp(k);t[0].match(d)&&(e[a]=!0,t.shift(1),i=!0)})}c(Ht,"getTaskTags");var Yr=c(function(){bt.debug("Something is calling, setConf, remove the call")},"setConf"),ee={monday:Me,tuesday:Ae,wednesday:Ie,thursday:Fe,friday:Le,saturday:Ye,sunday:We},Wr=c((t,e)=>{let n=[...t].map(()=>-1/0),i=[...t].sort((k,d)=>k.startTime-d.startTime||k.order-d.order),a=0;for(const k of i)for(let d=0;d<n.length;d++)if(k.startTime>=n[d]){n[d]=k.endTime,k.order=d+e,d>a&&(a=d);break}return a},"getMaxIntersections"),et,Vr=c(function(t,e,n,i){const a=ct().gantt,k=ct().securityLevel;let d;k==="sandbox"&&(d=gt("#i"+e));const D=k==="sandbox"?gt(d.nodes()[0].contentDocument.body):gt("body"),E=k==="sandbox"?d.nodes()[0].contentDocument:document,C=E.getElementById(e);et=C.parentElement.offsetWidth,et===void 0&&(et=1200),a.useWidth!==void 0&&(et=a.useWidth);const g=i.db.getTasks();let I=[];for(const y of g)I.push(y.type);I=z(I);const S={};let p=2*a.topPadding;if(i.db.getDisplayMode()==="compact"||a.displayMode==="compact"){const y={};for(const x of g)y[x.section]===void 0?y[x.section]=[x]:y[x.section].push(x);let b=0;for(const x of Object.keys(y)){const T=Wr(y[x],b)+1;b+=T,p+=T*(a.barHeight+a.barGap),S[x]=T}}else{p+=g.length*(a.barHeight+a.barGap);for(const y of I)S[y]=g.filter(b=>b.type===y).length}C.setAttribute("viewBox","0 0 "+et+" "+p);const G=D.select(`[id="${e}"]`),F=De().domain([Se(g,function(y){return y.startTime}),Ce(g,function(y){return y.endTime})]).rangeRound([0,et-a.leftPadding-a.rightPadding]);function v(y,b){const x=y.startTime,T=b.startTime;let m=0;return x>T?m=1:x<T&&(m=-1),m}c(v,"taskCompare"),g.sort(v),M(g,et,p),be(G,p,et,a.useMaxWidth),G.append("text").text(i.db.getDiagramTitle()).attr("x",et/2).attr("y",a.titleTopMargin).attr("class","titleText");function M(y,b,x){const T=a.barHeight,m=T+a.barGap,w=a.topPadding,o=a.leftPadding,l=Ve().domain([0,I.length]).range(["#00B9FA","#F95002"]).interpolate(Ee);Y(m,w,o,b,x,y,i.db.getExcludes(),i.db.getIncludes()),N(o,w,b,x),L(y,m,w,o,T,l,b),R(m,w),j(o,w,b,x)}c(M,"makeGantt");function L(y,b,x,T,m,w,o){const h=[...new Set(y.map(u=>u.order))].map(u=>y.find(r=>r.order===u));G.append("g").selectAll("rect").data(h).enter().append("rect").attr("x",0).attr("y",function(u,r){return r=u.order,r*b+x-2}).attr("width",function(){return o-a.rightPadding/2}).attr("height",b).attr("class",function(u){for(const[r,W]of I.entries())if(u.type===W)return"section section"+r%a.numberSectionStyles;return"section section0"});const f=G.append("g").selectAll("rect").data(y).enter(),_=i.db.getLinks();if(f.append("rect").attr("id",function(u){return u.id}).attr("rx",3).attr("ry",3).attr("x",function(u){return u.milestone?F(u.startTime)+T+.5*(F(u.endTime)-F(u.startTime))-.5*m:F(u.startTime)+T}).attr("y",function(u,r){return r=u.order,r*b+x}).attr("width",function(u){return u.milestone?m:F(u.renderEndTime||u.endTime)-F(u.startTime)}).attr("height",m).attr("transform-origin",function(u,r){return r=u.order,(F(u.startTime)+T+.5*(F(u.endTime)-F(u.startTime))).toString()+"px "+(r*b+x+.5*m).toString()+"px"}).attr("class",function(u){const r="task";let W="";u.classes.length>0&&(W=u.classes.join(" "));let A=0;for(const[X,O]of I.entries())u.type===O&&(A=X%a.numberSectionStyles);let V="";return u.active?u.crit?V+=" activeCrit":V=" active":u.done?u.crit?V=" doneCrit":V=" done":u.crit&&(V+=" crit"),V.length===0&&(V=" task"),u.milestone&&(V=" milestone "+V),V+=A,V+=" "+W,r+V}),f.append("text").attr("id",function(u){return u.id+"-text"}).text(function(u){return u.task}).attr("font-size",a.fontSize).attr("x",function(u){let r=F(u.startTime),W=F(u.renderEndTime||u.endTime);u.milestone&&(r+=.5*(F(u.endTime)-F(u.startTime))-.5*m),u.milestone&&(W=r+m);const A=this.getBBox().width;return A>W-r?W+A+1.5*a.leftPadding>o?r+T-5:W+T+5:(W-r)/2+r+T}).attr("y",function(u,r){return r=u.order,r*b+a.barHeight/2+(a.fontSize/2-2)+x}).attr("text-height",m).attr("class",function(u){const r=F(u.startTime);let W=F(u.endTime);u.milestone&&(W=r+m);const A=this.getBBox().width;let V="";u.classes.length>0&&(V=u.classes.join(" "));let X=0;for(const[P,K]of I.entries())u.type===K&&(X=P%a.numberSectionStyles);let O="";return u.active&&(u.crit?O="activeCritText"+X:O="activeText"+X),u.done?u.crit?O=O+" doneCritText"+X:O=O+" doneText"+X:u.crit&&(O=O+" critText"+X),u.milestone&&(O+=" milestoneText"),A>W-r?W+A+1.5*a.leftPadding>o?V+" taskTextOutsideLeft taskTextOutside"+X+" "+O:V+" taskTextOutsideRight taskTextOutside"+X+" "+O+" width-"+A:V+" taskText taskText"+X+" "+O+" width-"+A}),ct().securityLevel==="sandbox"){let u;u=gt("#i"+e);const r=u.nodes()[0].contentDocument;f.filter(function(W){return _.has(W.id)}).each(function(W){var A=r.querySelector("#"+W.id),V=r.querySelector("#"+W.id+"-text");const X=A.parentNode;var O=r.createElement("a");O.setAttribute("xlink:href",_.get(W.id)),O.setAttribute("target","_top"),X.appendChild(O),O.appendChild(A),O.appendChild(V)})}}c(L,"drawRects");function Y(y,b,x,T,m,w,o,l){if(o.length===0&&l.length===0)return;let h,f;for(const{startTime:A,endTime:V}of w)(h===void 0||A<h)&&(h=A),(f===void 0||V>f)&&(f=V);if(!h||!f)return;if(U(f).diff(U(h),"year")>5){bt.warn("The difference between the min and max time is more than 5 years. This will cause performance issues. Skipping drawing exclude days.");return}const _=i.db.getDateFormat(),s=[];let u=null,r=U(h);for(;r.valueOf()<=f;)i.db.isInvalidDate(r,_,o,l)?u?u.end=r:u={start:r,end:r}:u&&(s.push(u),u=null),r=r.add(1,"d");G.append("g").selectAll("rect").data(s).enter().append("rect").attr("id",function(A){return"exclude-"+A.start.format("YYYY-MM-DD")}).attr("x",function(A){return F(A.start)+x}).attr("y",a.gridLineStartPadding).attr("width",function(A){const V=A.end.add(1,"day");return F(V)-F(A.start)}).attr("height",m-b-a.gridLineStartPadding).attr("transform-origin",function(A,V){return(F(A.start)+x+.5*(F(A.end)-F(A.start))).toString()+"px "+(V*y+.5*m).toString()+"px"}).attr("class","exclude-range")}c(Y,"drawExcludeDays");function N(y,b,x,T){let m=Ge(F).tickSize(-T+b+a.gridLineStartPadding).tickFormat(jt(i.db.getAxisFormat()||a.axisFormat||"%Y-%m-%d"));const o=/^([1-9]\d*)(millisecond|second|minute|hour|day|week|month)$/.exec(i.db.getTickInterval()||a.tickInterval);if(o!==null){const l=o[1],h=o[2],f=i.db.getWeekday()||a.weekday;switch(h){case"millisecond":m.ticks(Kt.every(l));break;case"second":m.ticks(Qt.every(l));break;case"minute":m.ticks(Zt.every(l));break;case"hour":m.ticks(Ut.every(l));break;case"day":m.ticks(qt.every(l));break;case"week":m.ticks(ee[f].every(l));break;case"month":m.ticks(Xt.every(l));break}}if(G.append("g").attr("class","grid").attr("transform","translate("+y+", "+(T-50)+")").call(m).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10).attr("dy","1em"),i.db.topAxisEnabled()||a.topAxis){let l=He(F).tickSize(-T+b+a.gridLineStartPadding).tickFormat(jt(i.db.getAxisFormat()||a.axisFormat||"%Y-%m-%d"));if(o!==null){const h=o[1],f=o[2],_=i.db.getWeekday()||a.weekday;switch(f){case"millisecond":l.ticks(Kt.every(h));break;case"second":l.ticks(Qt.every(h));break;case"minute":l.ticks(Zt.every(h));break;case"hour":l.ticks(Ut.every(h));break;case"day":l.ticks(qt.every(h));break;case"week":l.ticks(ee[_].every(h));break;case"month":l.ticks(Xt.every(h));break}}G.append("g").attr("class","grid").attr("transform","translate("+y+", "+b+")").call(l).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10)}}c(N,"makeGrid");function R(y,b){let x=0;const T=Object.keys(S).map(m=>[m,S[m]]);G.append("g").selectAll("text").data(T).enter().append(function(m){const w=m[0].split(we.lineBreakRegex),o=-(w.length-1)/2,l=E.createElementNS("http://www.w3.org/2000/svg","text");l.setAttribute("dy",o+"em");for(const[h,f]of w.entries()){const _=E.createElementNS("http://www.w3.org/2000/svg","tspan");_.setAttribute("alignment-baseline","central"),_.setAttribute("x","10"),h>0&&_.setAttribute("dy","1em"),_.textContent=f,l.appendChild(_)}return l}).attr("x",10).attr("y",function(m,w){if(w>0)for(let o=0;o<w;o++)return x+=T[w-1][1],m[1]*y/2+x*y+b;else return m[1]*y/2+b}).attr("font-size",a.sectionFontSize).attr("class",function(m){for(const[w,o]of I.entries())if(m[0]===o)return"sectionTitle sectionTitle"+w%a.numberSectionStyles;return"sectionTitle"})}c(R,"vertLabels");function j(y,b,x,T){const m=i.db.getTodayMarker();if(m==="off")return;const w=G.append("g").attr("class","today"),o=new Date,l=w.append("line");l.attr("x1",F(o)+y).attr("x2",F(o)+y).attr("y1",a.titleTopMargin).attr("y2",T-a.titleTopMargin).attr("class","today"),m!==""&&l.attr("style",m.replace(/,/g,";"))}c(j,"drawToday");function z(y){const b={},x=[];for(let T=0,m=y.length;T<m;++T)Object.prototype.hasOwnProperty.call(b,y[T])||(b[y[T]]=!0,x.push(y[T]));return x}c(z,"checkUnique")},"draw"),Or={setConf:Yr,draw:Vr},zr=c(t=>`
  .mermaid-main-font {
        font-family: ${t.fontFamily};
  }

  .exclude-range {
    fill: ${t.excludeBkgColor};
  }

  .section {
    stroke: none;
    opacity: 0.2;
  }

  .section0 {
    fill: ${t.sectionBkgColor};
  }

  .section2 {
    fill: ${t.sectionBkgColor2};
  }

  .section1,
  .section3 {
    fill: ${t.altSectionBkgColor};
    opacity: 0.2;
  }

  .sectionTitle0 {
    fill: ${t.titleColor};
  }

  .sectionTitle1 {
    fill: ${t.titleColor};
  }

  .sectionTitle2 {
    fill: ${t.titleColor};
  }

  .sectionTitle3 {
    fill: ${t.titleColor};
  }

  .sectionTitle {
    text-anchor: start;
    font-family: ${t.fontFamily};
  }


  /* Grid and axis */

  .grid .tick {
    stroke: ${t.gridColor};
    opacity: 0.8;
    shape-rendering: crispEdges;
  }

  .grid .tick text {
    font-family: ${t.fontFamily};
    fill: ${t.textColor};
  }

  .grid path {
    stroke-width: 0;
  }


  /* Today line */

  .today {
    fill: none;
    stroke: ${t.todayLineColor};
    stroke-width: 2px;
  }


  /* Task styling */

  /* Default task */

  .task {
    stroke-width: 2;
  }

  .taskText {
    text-anchor: middle;
    font-family: ${t.fontFamily};
  }

  .taskTextOutsideRight {
    fill: ${t.taskTextDarkColor};
    text-anchor: start;
    font-family: ${t.fontFamily};
  }

  .taskTextOutsideLeft {
    fill: ${t.taskTextDarkColor};
    text-anchor: end;
  }


  /* Special case clickable */

  .task.clickable {
    cursor: pointer;
  }

  .taskText.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideLeft.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideRight.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }


  /* Specific task settings for the sections*/

  .taskText0,
  .taskText1,
  .taskText2,
  .taskText3 {
    fill: ${t.taskTextColor};
  }

  .task0,
  .task1,
  .task2,
  .task3 {
    fill: ${t.taskBkgColor};
    stroke: ${t.taskBorderColor};
  }

  .taskTextOutside0,
  .taskTextOutside2
  {
    fill: ${t.taskTextOutsideColor};
  }

  .taskTextOutside1,
  .taskTextOutside3 {
    fill: ${t.taskTextOutsideColor};
  }


  /* Active task */

  .active0,
  .active1,
  .active2,
  .active3 {
    fill: ${t.activeTaskBkgColor};
    stroke: ${t.activeTaskBorderColor};
  }

  .activeText0,
  .activeText1,
  .activeText2,
  .activeText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Completed task */

  .done0,
  .done1,
  .done2,
  .done3 {
    stroke: ${t.doneTaskBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
  }

  .doneText0,
  .doneText1,
  .doneText2,
  .doneText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Tasks on the critical line */

  .crit0,
  .crit1,
  .crit2,
  .crit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.critBkgColor};
    stroke-width: 2;
  }

  .activeCrit0,
  .activeCrit1,
  .activeCrit2,
  .activeCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.activeTaskBkgColor};
    stroke-width: 2;
  }

  .doneCrit0,
  .doneCrit1,
  .doneCrit2,
  .doneCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
    cursor: pointer;
    shape-rendering: crispEdges;
  }

  .milestone {
    transform: rotate(45deg) scale(0.8,0.8);
  }

  .milestoneText {
    font-style: italic;
  }
  .doneCritText0,
  .doneCritText1,
  .doneCritText2,
  .doneCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .activeCritText0,
  .activeCritText1,
  .activeCritText2,
  .activeCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .titleText {
    text-anchor: middle;
    font-size: 18px;
    fill: ${t.titleColor||t.textColor};
    font-family: ${t.fontFamily};
  }
`,"getStyles"),Pr=zr,qr={parser:Ke,db:Lr,renderer:Or,styles:Pr};export{qr as diagram};
//# sourceMappingURL=ganttDiagram-ZCE2YOAT-CDZBDz4B.js.map
