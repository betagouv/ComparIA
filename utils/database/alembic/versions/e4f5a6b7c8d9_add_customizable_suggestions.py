"""add_customizable_suggestions

Revision ID: e4f5a6b7c8d9
Revises: e4a8c2d9f1b7
Create Date: 2026-07-27 00:00:00.000000

"""

import base64
import gzip
import json
import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "e4a8c2d9f1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# These keys are stable identifiers independent from the translated labels.
_CATEGORY_KEYS = {
    "fr": [
        "administrative",
        "advice",
        "explanations",
        "ai-summit",
        "ideas",
        "translation",
        "recipes",
        "recommendations",
        "stories",
    ],
    "da": [
        "administrative",
        "advice",
        "explanations",
        "ideas",
        "translation",
        "recipes",
        "recommendations",
        "stories",
    ],
}
_SEED_TIMESTAMP = datetime(2026, 7, 27)
_SEED_NAMESPACE = uuid.UUID("2bf674d2-afbd-42f7-a14b-56a2996ea8b8")


# A compressed, immutable snapshot of the French and Danish suggestions at the
# time this migration was created. Do not replace it with a runtime file read.
_SEED_DATA = (
    "ABzY8000000{_i@ORpryb>?45b8{u&-ZmemAKEl1>PhQClhVu>t-FY-jH-&RtjuCYW~r|X1KxV=m3M|PqS;#5z`($8;GGNpBmO0GzVDofjLfQgyEz^VW+Aa}"
    "Rb@uRdB5YY-r4l;eCNeqy)%TN@$Y=+osa56XhR%&H-ybQx9`+GuKREtLf6W-pPgUVVe9*9Y^%Ckj|bllm0LU#*8FX_>%(2$yUlRdgx1R!aolcw#H*sL`Of)o"
    "<;@YVT6beVRQ~SZLQ@^(kE-?u*VeX>KgrL||A2qLIKOWEdg#MC`1Za!_UEsn{GeLz{BNp57xZcQ;j!;l&H1Z?$G1n<w*Fc5iTu&YtGd<T+kl_>Dzt;|PjU>|"
    "RaLt-R*kEotS(!ACVRFMr(O0z_QW;%^XnKI{Mq<wg^kNX2YHD*9$i0pfJUCjntB%Q%J+xB4af8Am-3ot)h~K?lBXL1O66Nwc_r^lD<oihS!5V`uWJn9<hWk}"
    "v^?9cogAY2Vhq*63mDt#<Qgw8z-|OyVH;Mm)8YKOlCOIoj{-qo4c$0+Ij;P#4!wL7PV&!gvjJ=y`S_V`Uts)NPUIEmF=hy?<qO;03m0Rz4&2rKv+AS3eFh*+"
    "=we(CW3Pb9L?d)1U%6o%;w^DI$QGj_ym9T;3CsnOeRu4GZd`tJ_>aH&ds&Gu`(m6OA+(#WKX3!FYR|9NK1L_Ul2tlcPJq;mQT|GhJ$7v^XL94Ks+9-jo05!A"
    "din|ZB?1idih}xvl+ofb`NOR`AvK;*3097D3TuIofWMJtcU>F&t&&~qhx=RL>!9@43Lbfw-i3&B$YMf`v-JcJ@=@&sf%T2wY~=6QjXMYQ`bYK*$N-}Y*3u2S"
    "7OYhH!?EceyfV+)_rl6yjUx$^l|s2w5W_mev{CFMVk3AuaC2BC%I>=LdOV(AV@n@{Q1ISESD(LX2t<%>x7IUpBZTYN;_vx>@l`=y+(u~Y@Wseo+;lw<S&tR?"
    "={7+}{&BOD<H$dBSHh~}1W+zif(u-qC>1YTcZcKP?|R?LA20Bn(jNE|r`eug3zhW_r@2{dQIQHrxnmf{CPRy`BZUf8gBrbk5#oA``5VE=(KU~f;2b<LY+L!U"
    "!pZkNP#6tt8>i>#{rMk9&t3Uf$0mc$el8yiH^oF>zBL-bkMNpx*Hb>o*WCy__5uZ2JCe|e;qE}1zbdkB+#1kyTVsrw)XFGMQWCOpT$w~R?idDaMgA#-Xs}%Q"
    "*afi22vPqM+Xg2HX~;_JLEbyy6~3vS%l<y?#*_ce-KiVn)jdv958FMdh^{I3$jBfXFMJRNg`xn!_kwMOVrCs42D=k|BSa#|6sq7q6s#rp7!%{8)9BNqdC}*O"
    "LDdbyazhe6yYuUn@3#ur3`<cn5pqaH2k|I}ICVrvcaWnt{wh14Uk}3R3ju0UgI^z9FRJ!JSaQ36F%p2XJDl#|MX7-SRgBA1PieJ@+^|aHf)K&+D4d3aVH+7h"
    "M;G+8%63NLJk857LTn}Q8bKw{cOsW;i5BGGgvo_*L=8Zr)y12izjOcBx06Zqv9P5aCSF)WKQ}u9uvy!W$a|C(P2k?M)E2rvcKxt0kk(B&t~%G(j~Gdb2Eaiu"
    "4~)K!c$MI36jMmfoK(drC=bDo87YFc0VdFLKPUMDxb7kP$sh!eDs9*)BD1LKyil;%5Mo<2VI{9KG-MMg+glsq079|$qEZt9#%kwQA#v|1kUoa0#eN>}DPAvH"
    "9HJXM?M5-Oj#N6rRYrR2QG{med$UKP{8<Sdx`Dd1{kQ+w@})0n1%f=UAf%+njXVD%na9;mWW3r*C3v1yAZ4>02yXpSEsdiX64mZOEL)t5tUaOOx$f}<Ah>ah"
    "r?7x558Y86MiKN4==oXoDa=Vx^moH3n-fqAicK?P|Na#u%-R#R_FU4I8*)Upd7l@65$;)y3E*oAX*_WZzLq6rTeh6?gHN{dws(hvDdzH-Nu+)7ZbdeBkh+Sm"
    "w65A86g#Ghk6oxE1$NyXhonblBv=rYpY5y$;q;eOn5A1HJuZJEqC$0nQuzS}Z`Ui(g$C-t)sDM|C~D8Y4GiQp9`@Y%pG;vz(J5eGS^rP|?H}yy6}ZOUl`Y}&"
    "H8=B@7)uBYVq&8$R3g={7!xAJgU7%BC>>A%d<hv)N2sY*uCb^=YErsaa4hmBbTmSRNoLDjJ&K90iS$$@9%!ak5z>YmI41e2%3wjnVoQnXvew^BoKPKwZtq_D"
    "Yp-@EzZP(ejXv~34kc=-li%IvRj!h6dZ+NjDJhS`<jeHgIzNQFBui9mzNkll;J!FTW`FTS$+0i-rXb=B@-?|bN7#z$AvBl#PG3b$hnU!tz5>7p*KCGsP;xLE"
    "9qMpJicTz%_$aHzIn@iL(HCmhhBwjBb~Xnu53a)flC~b<g`2CKpcVlojneNX3_`DQX0;>~ybW^*%-(;u5|e`doM4C&#ta4ln5_cCcecj0cf$`B(qBPDDA|gH"
    "o{63~X|5|Q`20W5*lNX?90nVTowKwmz7IoO9iU6g;`?f)``#eVh1Ahp`{RWTv2(-S2agyK-xE^~VHQE#3kYyQ(@1vQ_&$T=9uQC$+?jJOtc#W9!2p?}Y-y?("
    "E};t6mL}h(ckTHfg)``Z{$i|v#J=0eS}=?28`(qGis32pHy!N`noC|ehzZ+?9l}LlLT}btMeE_8Ro}xxd|<XS(cs4nL<`<92BS{8Z=O}>zrh-tAfCiVFw<(h"
    "Y1?#a-12>Gr%?mJ(cl>hki)Kl((^yTI*n?0#!<WsoG+aKZ+@{6jOg-slbp7L;CAXii$@XfOKU8`>XhB(AIeJdrsj(gVFaaIT^9uO5<rKq<DyR%-YRrWCuBO`"
    "h@UpnPS!C(MSwq#b6Ab);aTY6-bCPWTnPy0Yh%$<7hqUNisGuhfmshtbAVghGX6&Y)PpO>MmJ&fsS$zRW2p+b$ChQI_meMyXvkM5JJ!Qmu(do;ei!tW_|agn"
    "L*BMnuVWodkY@6Ff{YQPk$-kQ4H#u&uWmTbp==^f;&Sb#IEv^^k=gzVw>aT{pe3rx!bjao=w&j@A(({FYJpq()LFr0J4%;Q&fjOjA}j)Xx82y;m-`3@r#u9@"
    "2RScJCp4=BuP%=muEJLcgo^Pgia|KBc}g0nG0KfEgn;MvH|O6oB-g>WijNZr0GmawXij)!qUW08q(+%he5|g2JCNfSQFoFNpaHJ9AXWiGA$ionhk<R{QC2fq"
    "pfafNf`yt@?=xUqts823dB+ErOgTF)NT_MV_l07{TQuhSB(!hLu8LWcThItLDBW*vB|g0}U&8n=c%>fKZxs49PuvK45gE!4arw6Tu5ZZCPpt}_u<kV8`38c5"
    "vo5dhBljo<69f-qF*F7qV(~Hp<)cmirsdn|hy$#t<8h?J84ZgJYAT}~cR}=lyj?WS=g1G>H6h+sYdAHaW|7<*VGSUT;J08kh!jE0m6>>^uAY=8j?wK=&7!V("
    "8Z=}2RSsFU5XPYI=_`3mJX`tvnFhLgkuw1{RO9c4JLU6@8`VkPG-4&nk_hDxY$8p6Dt_?RMG<b#tIsqtt}4(EOe>_w;NvWz(ulbHQ1%nATLFTG9Hpl#Ha7);"
    "Zhw^jI#JW@_Wye`AlaZk+iH!kGOFQ3iu*O}f;Ww2A{zqKQ3Hd*pDVE(9vHbI6)zPz4S<$x_=F5JoZLdwA3%zgn6C`yS%!_#5X6ZE3KWSHsh^8Mr&in3$MKa|"
    "zo#Tak~cj+83JmMjbCm3^GpD0I%gW-;dh85nq(Q6!8?k8aocVSs#tD>0g?r15mH2WSJ1bm?;=2}vt>Zb0&D$|fBqIH%co&jyf|0!rsxq%NW6_8DHU2Ih>uI2"
    "fXQ#(;Cv||LJ?v^7av-I!dKDH&?TmZMdx$Ab0QisRSpasF<J*x5*Ep-57;8l*WBzv9J-((nBE<qRT&5ThS5HAPgRHCG8Hxs$#IElC_&0Zr_!!nKdhS$2vUTB"
    "4d7S~4`9h(fXL`y@OkbZVzZy^#^VXmd%YSDVjA2sn2fX;e4Ht4Z^1g#0haATVnyJ5e$8CYL1V@_8xUQ}cf#t9ia@WvAywA1k{H)Y3~n%TEEYR<$4MqpDT&zk"
    "eZxG(pWn&XKnfIxsH#cCSoSK%++j(Jxh&hOUOF1jz!cI*l*xUu#xY52KctNTQU@4AO0p5SKlzqvm!mL_n7QY#T3tK1rqbAoNVM};{gilkR;9er;4Ir2r?4<_"
    "$25%W*_j15mmJvYM1}4UW~%YoBJc-5g*NnjhsIYdvz3oR<#2=<%@AyI7;mechztb(@oyUWVpj>CBSKf58govV4UthHKHnhi4Jz$L81cy8sc=3Lvl0NLAf+@P"
    "hQ9)c2~55(8VnTk#V8_V&JmC){cww;8~vMPTHzN->{B<4g54eRDjKSYQ&bERIfrpA6>S+7KRbUC6FUbgSks8ZUY=DGXP1bJ$XjXj1EF!4$s%mKek<laf)10a"
    "G)If7-XYCH$KAxnXO2#g1^Hn)_;oEVV$NBJ#=<%J4)MpQeH7#}83%zjQd28wUM})#P<TYqY$(GhGW2RuF1ThRG}e%a)tqnC?1IDmiUL6Xd)=%k47lJYqm?WW"
    "$AfM@ZDac0&hZ0SmdWXO#1%IhC=XNE#`I?YRwPQi`(+E>n1y*h2UA&UuDNj<D<HgYe*Doz+~?CCX=i~|3eq$TVn>lsR`C&r?!hx`XgK@vNB{N@@}8mVnjsvK"
    "u9E#Eqb*fG$m{%DzmJD^mM|Zy_x|_~-~F>ceE;3|{|FlX-9P=q_uk`Q!cS0wC&7PUXjn7g5dAJ?B<XnT5^*Wa<%<&tR9<R8(#Qli=By5gj9CDU8@$!r1|29("
    "UBVl(kT@Sp{KyApe%BP4X*8+cF_k99byk8_RRUfYzPr@`h(ms!js<uTTzwdk`^zOetO2nw??|&m?5wGPr5h{p6Jpq?HWcyV*Sl6@Ih3a<pyz~U4`H|r<o(5%"
    "LgcEd$Npp%9qo?Z74#^^TC0Y64swW@ET|<D_gZLjW42@tUm?Gcvei&;uHXB?OmSjPWI4ho9-wN+1EK}sq|(UJj3{=r74>U!AGFTGBRL9$mwrgBd6xR9h7hvY"
    "=^2iUSa!XhCXzg&={%7K<$~weC)yhnQ&=Z<A$e$Wn55Q(Vm{u<)^9CXFF2QnkW6P}2XAe{%J&0;ohUCkg_`+npk9!ENI(#|H})Y#>~pYNU?YdSBXw+D4@1)S"
    "glGr?_>RVq;XyV@Xvq&F6ef<Z4hDdd5wVOln^s)~7YZ0!Sxro(4rWut;Vv{VtmLdTB5za#8^vV4jF#b>q?@2l6G=|xR01M>C~*|En5-N1J+2W8N-HLMf&F3|"
    "$eDx;8f2tL((H{gNumx@9#O-EiI0y|0Yd0~ieezg<#Rk@Q)Fo@_;b{>DoNw_EG`fV5wqcV%&D;x2zNtCb>qfi2Tx+1>f_{$Vu0%j7l8uN?UrDkyfALQq=a0^"
    "#&1%lWI)NC!QBlm4n5)x5n&3Ab(p1*3S8tV6j1eyIdEIy5YiiJWbc1F%+oFLrmT!J(;^Y_ZPlIsmwa&}1OfiIWp*Z-)H?r*VPqx`=nP~^Or$Vdb4KWteANA7"
    "tsX?fgad3)nlULk;xvPsxHQxN{RZ+;32cBJ3N6ex@;9`-D5DEpPuAa@yfW|!cYahth1?7X3*|xdoI;=c>=ZO5bB;X<cL-HFMCX4Ut}~bCuTW(K4>>^tdVZ~i"
    "sWH_gfKTOzJuRQw7ffr^n5k1E+djzxb&TRv&@@N8m~7|YV~tDv@hrC520`z_Xn~3^IE4;tXP#9NFQk*UHr4VJUr&j$MC^>=GOFiImnUrdzAW6_X!Rvc*uBc0"
    "mg46zqMM0Y*)@!34`jz;yFLSRp&eSkP!PtVVY3-QI5jN$sg~3{h}lQWm_ld%Zen-M+#=Bv;KPUpUt9gE5QbPb57AtO5KUo=s%=~y{8JpAbm+jaBZVE-NcE+}"
    "_f9=Hh*EPsjry1aLKqPtGba|nQ@ETQZ2s1~X3|5_&;U~nw&kI&%Q?v1ph1L8yUpT=7n%~>r}fyhD5t!(mPsafG7VLSHJt+-cTT{XZ$XM42-Ya_5U6Bl=ia!n"
    "Mp0kVlaY9Pg<T->esay2`7mSaCL0Z!6D^nW7T;^bF_r7ETBEQ)W3?NL@{U~NXT=d3oN^2u31N#Jj8viME})~NXajK{QW8zgJF01Z;*ZKurlwD!Ys@E|G<6OA"
    "2UeYdCHe%EBMO0A%_qv{v8^7NK{c*duBEYeU6rHKkcsvpEMrPN@hrR%jnW993@i)d4$f}SqGSRE288CrX$oI)8H(3iCKe%qWS^sY0pW7n@7&y)$(u*GBeW+N"
    "<wEUAljOF6$v#j6IxAP`Ve#cXYaAzR<%%Y?icH|36cubYl~hL1_&VXP+zhKn1sz4@sW=%^${sH-wSveQIt>hIrEQb|&lY0ZhPiPm8E0-X><EUGg;g1*jKTo}"
    ")iUwC!2yzNn8`FTIN6P$m5l1Bq?d#B5}Qp`2Y7{w&mvAZ*WJx*4M%hCXatb-XQA9RG9|P{ee8$HMD!`eCt6ixnF%k*bd$vB^$<aFXQpN5<~cJjC1{=L?@n~x"
    "sCG-~N@(!3P~~8wQd~F1N{QSG53(?gq921=;|j_J#caZ>WFEyqPn^=?eMa^KkD}5RunT2n@O4S9xp`0ld1H;#n2O-O6Qf<J_?nVWPDUnWF&Fd~MIQXR8Mf}n"
    "HG-kF)l-`fn&FodDG7v`(FsfXm};{`8p>E*TN*5YA|f~Wo!`R~Ul?EJ0>e0QG-W5l3rZxDrJ?5&QVJ*mTdRbZ#}AVTX-4GSvaE`eWzfj0>!Q+n?(j?qE@|0q"
    "P!@^OjX<yO<`M28Z_I`GQ{)V4*fJQ<@)(m<;0=?AmxXOx#PUqxBm|fvtAYENf<o@Xi7hqs22~iQHMGi)8K*XCBqBod1;DwG8UU$zP8!Nqd0gKlEacFf?rd&p"
    "&NN9D7?VDWxvFpB5GtnCNSoFYP#p!q=YK&6`bOIbO8T7dBFX+qV$3DK=9jXYY(zhE0vK^RT}SHRUM)3n?X&+@>TFjUw<zBqL!Tmv*+oUwe)oWO7~ficq)@)s"
    "grw#nbq|H+Y^$^sU<5Xzy?zLa@0q<DP&wHPn@#OF1%$QNp{0%Q`ecad1JO*j`IgF>S+e)ewJA82NEFrWeRt}<80Qg^wj11GYQvaOjC}0Y_&F@EfPhcPp2Xwv"
    "nni~jG`*ZHS#V7eMvC2dV2sbay=-_C5^oVsY1s@S)}Iwlm0(z^LlZPY$e}jwnjW01$60`kQa^VBoPWEeG{+vT2W4RaCta7g0PM{OW;UXGw@zVg2z(!NPD^uf"
    "wb$}|iYhq&vQ2nx(ZY2qIIV;&9(?KS{QKXHxm4JK%Xa>3A6j-&t0^p0<7OCTa97Y5T8(5)F}0`kR*p?1p%j<dx%foH5Z{gcnqK`45M@!2StT}JTf4s2Jd_o)"
    "Cboad`?E6H9NHiYZ56?^KvKTx&}lc^ERtAXSkq?PoF+Ay`#(%ywmIOFImz-p28-L|-Lf0Nm?F`#r(kKGj8;(ZvZANYi63S7BnuyjLuhX=OZc?lA^A9F!4@>8"
    "vDK^4Osi=rz^zyp!g2VAD7(<nW5X)zrVNJ^yD(DF1fQDi7FyBZ`cone`AJfiWhV=`&Z4fG#cfgmRC{OCApeiQ`FrN+EWKg~wo>_iJF2|2W-PNP=_*ET7!-tO"
    "qXSyHwSLzWb4(VyW&N~)YZ0n@!lx)A+xTTE!^I67VTBNqy7gQxgvK_=tT7#Uw#F6fPQyGj6;WHWZOONYT4;<XQ|`7;vA|sPs{V`vjB<dXsOHP{FluDHVI#sk"
    "8hTUP=HOm3FPZ}Cz7<u)qRf{<UIJ2>(YMuu#!SN05-n1sHd*U78@0Bzc(Q%UEK6?0)%fGBHPTkJD)8#!N7N3C5XMyQ+^wLW$aGKeZ`Sr1<wf&%VL_nXUKtRD"
    "8?=s*Pn`LOhjFk6Cx0qKJ-JjCCY{HR>)hK=tL(Pk;5cPfW0_V}Un6X^lyEQu0eu%srbV=4=Y~}`r~u9QM$9kug^2P6c~7NA%vK=r4ovsK>U9wQ0aZoB7dFw_"
    "5ne4;e1hf4g60g>+N&wLS%~_#>f_gQ@TUVWiD8lynUwXTIWbQ$MDWOK81G4RsRzU@ExJ#aO)${WsV<+AIYqB$j#Hg9(RJs^non|A&e0#RK4{iiFO|$JoCs^B"
    "rlEW-CT9AgNbEoW&TMxzGz+!&sK0I5294T71@K|Bl;cD~md}O?gWF=(3|flLUk(0ESu9q#Y4~2Yy>q>oT>MEnNaE=Z;U|RHk$u5^DylmMR;a3|oY<I*W+q_o"
    "<VPB;nW6^O$DL@?H<Q^UykCx6HA=T?4^U`(#%J}N@W}hpC1*ts@@jN#77n8Zk!uZQmu1s-2qt1tYLkl*lSDX76%$%%6LUYC#g$F$T{MV3At_6Owjj>h9Z4f>"
    "w4c`yO!*;Qut=0%B<tU#9h2pqBHBn2EB=D!^v!@@(w0Tk>r#);4M_Rs`za=#dh%o!cjRfY#T5e(K`BpCPb6?DHc?=<4ZS*-Aq%Ttauh{gXc3rh7R41)F73`D"
    "w&mCp$}A(>wJ>}t)tCnkbd%P+5ZX=e@=H(wKW=k)<SARr(R%JxY!s6B!p!3EkXW|oM4h3qzNoRdhTnx<X)X1y5>$Mvp>>se{O8lMp@^$l$m80wQ$#eoS-D=i"
    "m{!nRMj+b<IP9AGZ#JzcURvynaN0bhe1)BI@XHScgKBhS!~7Q;q9_00382!Vw`}6P#2I=v#gP0^+8t&6Qk*;{{|W<d77jKNQ>9&sfQ68%5I_MtT{sQLNu~XT"
    "fTTWy!eN;L{cLSY5)c3JK!Sm59>Pg=N^8gAJXt7QnEXX)`(>0=lwnLsow7If?V+7am`0&^)xN-w7$fa-_%f?lMen0F<BD{#3G3-y845-jbvBv&^>7=^GBLS!"
    "s(_H52$za=ZjYu|LSYTAT*LuW0pg|fohxz9i%NCu4B=MVf*q2TF_Y0xs@!EXd>Oe^#kXnTpowvTZ9+8n2-n%pwj(CiJgM-?H14eW&Cf(K!WcOpkzLW;NCulo"
    "YZA&r04)K^?(-uCQ=x0tu(X86QJLD$#?}<R?c@c{G_ZBhz1a=PHe|FG8^&jRzo@Iqv}%$2>`E)s&(!rqYTwX`D@r_?GO2<&F8!9eip#O^Ivv_Fsums4dTK;}"
    "QcD1Z!kdCfSE;KQm@s8fSv#5r8i`$P#rGICqdUq0fI6FpZzS%_CD9^u9M9sl-(a+8WXh?k|6l6e3oV3nal?@+IbtLp;Tp!i@*oZV3+F3!K2DjTLY$XV)-KWk"
    "#Q{q9XySGjl@8)yXbeZ(O09d>+Sl{HG931HYHseSA>@|E5-2B@M5m2snLI7zYIU(zai8KF7dGP?1KOEUC%HM9)$<_Ctj)hr2|1=Si@I4nd~(jFS||&l$<ir|"
    "!2u1I;vT7sZBj{><d4jk=ztMjez}^tC@w51jIC_Yu|*Adm*T(LhHFV%ONNSHkS4r5QtG727}NUvsT_(p?ceI=AmZ{QoaV-uK(Woz9W~?@!lqlGa2Co@_P?2&"
    "xQqn(5*mdxE_9P1JatwYZgnVBISh>(PG`Q16TC%PX)zB`^vB?H!$wh-mOud!^)?xSGPIb&zMU$^S?QH}HO)-^XVI_cGLy|(*|LFjMYrUV3FiGvcY=}Ic|I|v"
    "DJ>x3%QEh{YWA-<_iL)_w^}%L{nt9CWUd5L@Wy()-&C7ZU_i@==PG;#v7!<>*|@9$g`JjKCDOnnZ|yE^@K2G)Q%U$D!r_Od*`p>3vR-1wt0`_4=3~Xei(w)^"
    "X79sAJIN1=fPs2wd^n_EmqSFFu-y%-u~|JbM`S(;lrCiQFjt(ZFbF`=ECAc`1>2?W6>IN(IAsCR;WSMegV6q9n#?ut;b=5FTrcJ$=C(fVdCx6ftfH!&R-URJ"
    "Qdn9e7cDo$purUbHm;$#+Z45_K17-SWT2-ZajaVrrTgN)-CJjjnlP)E^eC$re|cZFCaW`ih>tXF`61Oqd!tiS87h6MG45E<#Ug059Zc=OOjD50p%EcQca9ww"
    "Wj*w_#G6B#rF#_)<Ka7UsG}I1L;SY3?4>lj%1Mj(WB%D}Uha$h*Zl;Z)HT*1?!|cr)loxW^^}E!)@nQ0rX;XWyrOY7bZ_b-OFd=x3_Oe>=2?q*lG}}u#MF#3"
    "5kL-VYSEOF_rV;wzdq#a!>XWYvN74?tCU{O6SXEPz;QDfxPCJp%;u7fOygfs<OJEt(WdXed-uV+=z+hj#(t#)wm~SfwSmH)+*se9v5_D<+pCR%E7gMlF$*$$"
    "0v{iyGb|wl<~XQ(b>gS;v^XV4NCRDHO@s7=KFKt<ShVW_N+Dk6*S4^)1Q0K1Qrzpfyh*Uk*0&*0^Dv4VhL9p-?7?YsIm7}yLgG;iKL*lkpF8PVHK<af*P%<z"
    "($A_Nt3vB^K#F!`X=85t8%lFn{9fp#<v?hiYg5x;qn(avRJ#w}eRNhF%5J-{v6_N3?(g8M$wDb6ZD~V8F-;I+^bS^QnA*h;zSXMinOOft@61KL5bZzJ7;?|T"
    "E-Qjy)Rm<<m@u)B?{rIGmfXF6wYRL%!JS@voyKYtnnU%gcYdOUczKYGEcdH-@bAx$!8e#a%4)9{D2G{zhz;?6US@<N1kRygdwa4ZZmdO*{3EaGdm9~z0g&;A"
    "@9fqP;jO-Knih_}XN(HqZ}hD9RjL!g+(nMqhRPW7oP>l8(XxScYc^gtk0zeIG%t)|z;d9a=Kc8URI)_}Mr;l1cNN>kR8!utuW~0m2c7F0xdobnPuM6=?L|yX"
    "D^585wu7IK@#R0}&|`imu9%v31EyJMM=?4LZD@t(ao~Jkj4*F)c?|qO)2>#YngLWy+Kp_Q#xtBRt9tm;hn^M%^!PW}4T5zx^@I~i5t&UhCn(BF_-o+a+b}rp"
    "^%yX)@GY<rGcL5u1vL17X{+TN=8R5muJ6Q>6HGP}22ZT?&XwV;zTdW8>U{i^kE|CU&~i}Ek+t$(*B_Mzdv<NR#ejz!&PiWam>j~XP3&Ka)kn>7IXF5MlPJG*"
    "aAVs0TsxGfI9a)#Yuz-K$6&B{-?5{ifY*t!kw_P9Lx-^KXA^HB*^@Ry>xOH#sb)-m|4)rCCoV95trKRB$gyo``Y#BjSUj_7I*VuvOpWE<PtG8jq5W1XeZtX;"
    "v{wT4u2!he#;U$Z0}1YJ?kuM`2Au|g+7b|I7V5Xmc%^apnBb7@+GIn{w=s=6?)@QfK5fuZP{UYrbXbyv0_h<EB%o&CX29TN6eF*K<5-XS26~Q;!(@AFGxKPJ"
    "{45BH0gG8C)w2NvoH=s-9|P=YYN1i<w1hEtouS0x1%?sbL&x#gZm_Cihaeor+CR_xcxneu?{;X4F$mKF<un82><9?`GjLlXFU0u}n3hF|DlbOPA(nsRCI40I"
    "h)Pa@D-c9Oi`d)!`uyLA-`rL(E(X7o4@4BLcg1KVSl>-_IstE{uRrsYAeW99=0S-a*N4KU)Uct79GGA_T5+MZSKY6hM;x-N!$MW7>Y&g;-LExgI8`r|uqlyX"
    "EN%L*?W*roFT|#%X9_NTPpp;M2k+l==F04|5AL(w)3M+|C)*e2OUJSi6!3YNtj7*9%#gN!@ygO-zsbY8&66+3Q<pE_3YX-O@ijUz`$4cK#$z%1g78=jfY%97"
    "^PSq{^Cp|($w{NZCr@L7=U;-HZxys!>tmT*5Y^|@j9aJoB+SP&6-VVPvydaTsB~DDQn;O(<Q|)+p5|AV<7{!3RX2jLSB{;%i|Ksw>z}$_XF%N+i4GAhylUd)"
    "Fs4Af76wuKQAG8ce|wfA>AS(}bb~~&AXp-9*J`fP=GiD4+znawS@=y=zwFvO{NHV+(49N~GwLZz%IM{%ZO3Uckmt~xaHrP2KasmMdaiIQvm_;sr}B#RG(<lm"
    "ltZ@ak$%Mn(@wVDtS}udu@k6p0+OZgSRM9ov^G_Hz^8G($2^82P8G2+@pSCkE7(kQcY!6*;OjMv6snBg0<s@*#v5{=no?MW)*|8ho9G(OI%o=#viWccg+eXo"
    "-wtYI(CJN%)Dh-GYNfxd2NO*FB6z`n^}T>B?=3YGa2FHBb9T=axFwRE$n2KOj|bZo%v(-Z%Ypp_F$}O0GI;(LtgE@3uZC-k`<dG^HNhF8t3J%;=v`sdC0QAl"
    "UdQS+p1mM_*~CxXM)>8x(MF{Fe%h4{?C(akS1D#R1`^%4w#ofs0q#V4-d>}($$DFlq9-(XDA4<<EN39ja}&}-(P?x)j_W?n`%nscTJWG;ao5#;StU$0jysR4"
    "P2&zL$k1=$UkAS*5y|;>)|agwBGnff(v>hbjFsq?mz1={Oh7G!;k-@7h1CPxbQBTko)@V8CEX<P?iW(uC(#aRmf##G@gz*2<okDp+C#gfnNi%Mv9}p#ZtZp>"
    "DDk!=rrW2fsFYxr+y}+t_U;b<H*HG{gl(7Rb0x94LE~Q<(dvZA*XVQwQn_jOvNL~pOzc>xBwwha$Awh}y?F<JF$Tow%%$)P*i0fv7>_ww9qO*Y0h%Zf@W;RZ"
    "-MC3LXWEe@7VS3^>D3S9c)~_2@n0~_7D3d+Z;Sh9O1>=tXpbWIkAxKWgM`Yqbq6^d$KSBrygvoipbX%VPq&1CR_-emJuXgv2%tD@HGVN(Y8;JZWH1nh@|DiU"
    "(v~)s7U@kz>^EWhpzWp_9;8SU%iO+=rm{sm$Kj6Erx?2WUG7hdvlxH2iQNVFD1PBN_vhaq)9Qab#rq$D0YwNp%PYo>U_FLd+9hJ0YFxWRX`41IgIFegt<Jpl"
    "5>AL%_4;oinck0fxxr@^?7VUUj(eGrG4YNoMs89Uk$Sg_afW2XZ^daSUiAmxzPL!m+l>DbWGZlod`wJN>v$T>#!#~seKl!J-F($~B;SV4sby4(gRlj09hY7L"
    ";PEr?6Q?Rgb*hFAQ+41X@V*wJ^wTa4IruaTy}t}Rr$ea(D{;pr3y`WQdu9m8{1^UGIV|tmIJBvrb_&oVGzn7zS36)nm(H?WCbT$d^6vdNc~6%&ukiJ0+$+X("
    "T2e&+d4HRDpIM~TZYX}xp%{~r8~3|~EyR|9DGiZMLkK}buKnF6tW&zO7k8$wc@04Ik`Z~U3=orPYbvm)=1;34^ry<w9dTKpHXHb93M^-;;+=MD%tkL-8FoFD"
    "r0{Wk5ScWqPq`ipCrLga2T_g&Pxo!`u0r)p9knmY{}!`+T(cSvv%59uOb&Kxi>?<QCa!vOzrocv7<}oMn=8?Yi-{1&=G}<6NCQE+C7iYXhyGcyEu#XTqWx?Y"
    ")(H-?E56?Qvk%{0ENhqg;9Z|9-YSP-NSyAA?YtPkQ8_cfsC`;7Hzb{Zf5<~qm#BLTAB=U6T5~m<nQc=bE4M<XF5l9U-f^7;W^Vup^#-)IoB=5`(x#RL5hXU6"
    "n@a7Y7*rz)`aTx5c>d>=*&^L$lWQ`dDvs&)NgK+UYLU}CiCGm~;wVr9BRbmfltPwG7zP&A&{fvVThwa^`qcYnVCre_l&8GqF<I%-Pi5ZeRtiPNqKzl!d6zMd"
    "F27(Hu>4fHpD8}`%VuO!r1Yp}7nx-D#BM~3^D(|lH!_Q2?l>k+$riI$2I6EGf%)-n*B!5c*eLRb-7ZA&6raQHIvvr10Tz9jic;o7SuXD1ThJQxxpvDg@pDPW"
    "7euI8Fb2Te^)&JEPz0i_i2o6}tX;nlsX!y#%V|L21Yf&#w$o<Um2b9wQUjZAJx;y2x#v9rD72eql-+^<UCOK27-U~g(@#U9Y-Hsef~8P$!enc$eJ_F2X^l6;"
    "Yihpk!>eh;#Rf{}B(B(OYL1oqml(PrSV7t7ZK}wz!#FITBR8#|U9I7-Tq~%GGa6szYPKh3PvPca);((B4$gu!<*}7xq36cTvA8k-l0oAk$%2Zvsi>x$j+)xY"
    "N4;oZ0=1Fl48labrpdgf0z{UoVgBeH1_gri1)N=W#kF9TiAj#kJ2u6wpk*o2y7R9<S1HE!sBn2ibk}wxfqL90y(&dK9!z=VzjY9<x{9l=uakUE$Qu9@CQm@0"
    "Y1_AY*Hym_ZJq?22fa3-cGIZL$M8K#!`>asjXy4t3=a!wP$IUznaKbhe#yc(esWb5pqz%WQ0Oe(l$?y^fiaa|6!IzYdAh*D!LV_eIcGq{PJ6#$m?~l3!~!Vv"
    "K|JI<u9W~bJxWl@pM?Z_1L7C@tMnjLSF?UEr6p5bvADtMs;*U2JMDRRTv}fjO$q>#m0yrmo-kIF)UunzdUZJ(0RP&J`JzLcdKG5{G)Y7tiG*3w&HS#vYp`On"
    "82z33B1hf`X?l$P!i^5DND~v$C)4R{I(9wkGzhLXQ!ld%Lzb##W-O{Dj*_{x4H>uW3jMW%pDx8**fvwu%|yVH%w)!giAl4o_3kF#Bhk+;jD+d`g6U+VXa*zk"
    "x0*XeW^!Iwm142irk;z*kk}&z0gr|yyD=5oPve|yqgGzan@y=a(k@{<qZP=P=F&@Cw;L@4uk&%?<6Hwt!PCtoY%UDy<gkeT?5r_C2U;vka(<Mw$%V6O`N)1&"
    "B5;w;>-KlT$?YRv>9v{>A?WwseHX42=GwE;Cs*;ibc61%-toVBN2k0Nw?>%Hq!S}?8`8X7z&wqu(5YR48`JFQcxN+4%1rC5M!~Av7Ro=3V-cx|IT`GmZ4JDL"
    "IObFF#uMQ3TWLZ*wvr$7rltfxh^qYf;I^S%RA2DYKm|-X_>}0?!Y)mRrfGB>O?E=LyUvXOM^a5s1yok>Q1xSPg&)^Ya%Hs=)Cly?Agyve+JR7wG^Q)FST4d("
    "6X>*tYkBR_5)W6QF!xpwjb)+ks6!(9mN}w)R&Bo1)s=K?YVe`UR}K%4!XVw#sW(qx8=s8eu>V4z+#s}-y&UyUZI7D|I1Q<U6$V4}oa0DBv8xW6n{JKi;ZGg<"
    "y#?y8(7ey%D<%g?1i?zDgt2P1EsFuJE+tU>pj@i)CEoLG?bn!%mMO=N=rl-kQb`9QtbTH%KO?1T)i3cCwk<}~TTL*FcSgG!A<s7(XJ^s~+_Sf56un;=T{9KO"
    "8&HU!x(7LuO?iprh0VzOO%rMIN`UCr{dCc#=om4J7DS>I*H-M7iyhL^87T+koN9~0Y*>+M*Vd~>om$?rD_8!F!mgO>cMIQma>Hk3H3qiC;z{l-F>j<w%yW|2"
    "6*+@wHA|UCgdi|%VeF|mfZU^9OL6KNy|nsGe0zJrOgE`k?{SgN6yer$h_}P&nn{AJT(@$oIXPH$%&gq+5uvHch`ubTT<`n=MxBo2$L@M`9%0OdP@vuCwIIK;"
    "nvHOrpCo{8Qg<3t2rTvO)vdN<Mb2iZpuWvI>xZn$`k5G%j{?}p?+W%XTcr}Q!|M4S<T>47E;biyh?Sb}Wa&#m_Y+tBpkt26|0mI_HzqO#n+6TsW<H^8A%cmP"
    "sa{|9jMU%jHf#?$;}ceD-U2tm$m8Kr$z9O(dmk?Kr`S1&WpBH-pfw%%Ds+vIoMW{;GBJKkmt#y=OjCdoBFSZry#bG!5?b-2X^Z8Kw6k3NFwBFSmTBDy0dO{X"
    ";g09zPoH1Q8LhTAm&qYiu^+D>@>4f9)yIt+Yu`KpE!|w9AdkD=+3@_Jt#Rl((K^TQO84&vYf!I)Cb{()!b7AU+Tj))YK45oIz$tau<Z5g$uKFj$3-*~Dvle1"
    ")2=V{eUk>Jpv0p&?%c``w=-znbiA!yzqIbZ+oIZ3OXjH~b}%Z=|7=YDn3{Z?-gOp7qWD<-G??}COL@i5;8tfj2LX@Z#4Bd=aKYlg|J{hIR0iIm_4d}t4}I6e"
    "Z~N5uxI^5o6rDt!y5uJvs+T6vxl!9?tZNU-_ff5y*oZe$*a38^ThIG?UBg@caz-~JZHl2<=AEBn6ckJaWlW@&ActR-7-8nJwXp|<be@$r`lSBmv!<RhWfN69"
    ";d?ZzCq2Mfpil%8d5f3*MLOZFwInN*btszF5gBX9Cq)1JV)rIdJms=>&gl4K-`C^+skKc@8Nbn4tZ`uJIPP7)Mi$EL)u&+H9KqEK(Gc0px5s6?pgSFrqxh7l"
    "U#65u3-bxhf;(3;=6lF<9JQ5G8(n1cxU7l;^M~YoTwU*qLh9hj{{RE0TIj`((O=zOgItP`wcZ-lv<NzfLDeR<3)TLgpSV(yeR;s2xnYO;sp@klYI__Ww{@Qq"
    "Jt;VqHmgPj=jTo1^Xyi$X<`?<y%-?QV0?Q@o%j_!4)8scTgGsw3BI{${cu=yO{%bosikQ>!^FHQz`7--bpkFzSaHIWPYXk{3{%KHS4@PS$%tuGpxuJ<iCZ63"
    "BR&S>J_S3<88JGmH%%8uYNoBx6xuILzh66+k}iDa6WbOw6OzVZ3%OvrZ+-I-B8Tmp;9zBUykTT)<)2<}aw{5FF=p1qbj6w1+e8?}D$0r2u_1crl~!HIfAM?H"
    "R%|iF;!()hIbDsy%Qa_bJMntgyk@X4rw~F<1{DWHXkk;HmaX&jV+zR#39#ur7Gw8Nf50oz)lGhCJE2vriaS^+&Gcsn6e`(;mE4Lb%4rUQmOBO5?dmZXHdU$s"
    "xzL5?UKrL{W^QRCDh_S;Cy`vfY-2QAp{MQQRk(S|e8PzC(Z#FuT0jzpUI8)9&AZjM@Cym1R<yPm#TiXwxFUsNLEFrhSS<Ki^~>o3Xw(#t(}P|75Qqt0PGx!o"
    "r8sHkziAqd-wy}93X2&_dq}etQS?_x<A*UlfDyuHMc7uubJl;7ucewDaa3-+axy#Av+855J2P0=h3Skj!W&1O1}EOyN@m&LH93>aVx#5ogKJTm2}hcTa>4GU"
    "7TX{`+`@ZDdO)ZDrn?%GG{`ouh^uW;mdmj>Y3yX->Fe!Qmhy_l&8nzY!b?*Pee35p652cp8zyZy;pLh4e|>-ZPVL_L&WkA&{82d@XSj$5|FU-d%D=2NuTcI}"
    "6v2M9KHD-nEPmH!cqB6X`Cgy~D%=Ar{_cPQH6k7>w0X2h@K@b|cNT_bHP$dP*{b9lzaRRr_x(M-(%}Q>L^}v2)N}}j{`~d9ZC3q*xIt00@F#v-#l7gjoj|_Y"
    "y*z)}95Fi=sg;f{*Qh$MJfaxEr?jE&7z2Y|Fa6>CJCwT}&%Xn!;Uf$h@b&U>eMFXzd=a<GOr%W!i+iXyw;$41F9tc<rfb99t>v@*aCbkv^eyg4y5;GFHNy!n"
    "71dvzf7f$*7vfX$ioBqh1GwQ(te&sixc5N(9*7XId`W=B+6~=uzijMp=EpWXpujoQxb6q;6`zP(mO%kSZTbivO&qRlREY5W<uK%>@u2RIrH~@cQ8n9Fg2WRB"
    "N;&GIpNns-ott~{^`Kt|jv=iDkvv91f7<!s{IyQUs1&ch<(n_IQ@d?s;tsJ1?nnMB2aLzD-48&WP|F~2<E!<x!wg(-UH8n-^B29}cwq#z6@f}cp~|0)d=uRP"
    "r<0$Ba!>bqTtV0<jBL{^<dqwgSNhnD1AdjDgjUNTY}peZ;$Fu_XdLcM_%oU3RiSN!R7tmN!mTlE3kd}r#3`8Mv3-Nc#FlVEq~QF!t#C`tum)csdm>rzN_)ls"
    "9@D4xD(YDjCjepn5BB(@6Lar^#hxT1>YeOyLaPnt+VIWiubZu(F^bU4*W0uR=928kTH&_o{b6_h5-$_Zf9ZiUq|kTWNg+1OF6aWuoI=0HyPiL`p_YVoLd`#p"
    "Z?v3<N$p=FQu!!Uh=J@x7+fPSU$sIqXqgS{6cnrGB@8&sI-X4*)5$l#Yjjsm(AX2`D_;ZK^1xQ!tPc*h-z1rIGs>XkLy>j8v8Z?jQN_v%iyJzbM<%it8NkoZ"
    "zpF2V{SSmrdiesc-gl8qp;~((<JV0%t~%G(kI4B1?tOPSV)##QAO~po0w?j=&R_Nfx}ad!HMKI!$qRW3Eyg|92aJ9o{1Y1r-mTg%I#LB`Kv$#8oo^ktzD;Db"
    "6LuMRBa=KfbcRXvuuiyKJ*dbG`#qvZA_*`ISP;9V_NfyB8YmB0NUfGFuyq3R;R&9<<juQDBpn=XM@8s!E9Q)d6QO1Bg#olcvfy6`#t~h-qmf#L5SJ}Kt0uaD"
    "p(8~1fGf+$H1ckME-_H;PbfxzZo50lPOvK9cNj$xGzYx@S@q|R-k)n%euLr(G2t+Z1ZMyi&R>(11w`2S-nDvgffoo~+ZgQlE5Chc>w&;If4!RCy-Aqz_Ki*F"
    "Bz(vqU*hl|ybEER->CYEl4}r=Pc$2ZRX{9|4k+a%!GVb|N@`H$o|XV&SN*t65>oyni0Bj4?ee3m=fF@&2-pm$bS8+h>QC}Xek73JKMGX>6o8!rm11N+!U_;`"
    "$M4Qx_xHuiCiGS-`HC+PhpIzULGLFkW%aP#`V!laPq;kM^Tex$5-*NzjhBCuL#i|Zy0Kso7hn*(B$fg-oea|lV3_(VuK^pr|E@YIg9<LdtxZP&|0@~;rQ<?W"
    "{U9qS-(QL>{jwru=tv$r&QfIU+;I27Bl7CIo`SY|A$qU3tutxS-jf*3dW1mTM-1<!zQY`nUX9f$jcIxKJ?K%;4M0G4d~XEroWI`l!kGpv+&`<*?s0Yue;vGF"
    "H>qpi3PM#@Jga^vyCb3J_3<kQM_BEmKmh}t=b;hc$;t=Ms$bx81F>@kHHH(@K>GEyPTe6b3!ZzwQu~8b1^QcxY(BMD*&~Yo(5hLKcK*Vi8<br4ur>u~WJ2_Z"
    "^z8zGTd`p4SU=E~`S}6(rvEs-NPZ8h*PM#)w;{g{MoDkOX2thdycsheI%ayoS6eZ|F#G$<em|VQeyIn;%pYh5zg(Qi#Bdd{BZveX0xD_W=pYQW&9IL@dsgjH"
    "q6804Y*#hP5<8eNW$G>;X?SS20vs6Rpz((o_A?L#*)pavh=0&{*7Yg9K&(+C9R;qO;z+_8JPMijiHa^4XGfo{T|ca<M#;MR7B18j_XS;5?e^PAVgBj-NYCGV"
    "pgr3$^dR<<?ZcsUF?hUTqIlh-98k>SjfkMQaocCr&&>+1UVKli8Q1UAyu1h@DxR}HDAL<*>&*ru4ffS9KmX|F^4HZ?Y};qcadQ5O!1y6(>ik+>{lH1D{K+>P"
    "A*W(hSie>j%_hg)rIB*NEib?>_aw(WKF-*FvT15WuRcho0e6&)j{s9p-Kc8cd$k{z{=g@bsi7*F=EU4Veqn!z6S7&@Qz`=RqYrHA8CSu3D8x|@YO9zICfT+R"
    "lfVU{UhLBlv@UNaZ#j=W)6<#QZ)FoNU<z;h@pwdC-cmPViyz|8*f^T;L>}(_62a>2^F)8`gSGYh^odR}6L|w+a6k+V<z7Ng`xD{-f@o-8@TI^$ffAv4@VcUQ"
    "lN<s)yZUt^YXD#n5DRMe!&6}WaDoGme=Fc&7y)%5Uvg;jZlnps;4pX$70x?fU)_<&V<Cr^ZmW6+8-WOkl)q6_K@A4`9xI|K{vfya<o=C640KDy-n})i3Hn8i"
    "V8~ny#)8zXtM@CtZBc&p!KAt~id5=SX_vOA84JMf3voMCpbF9L%%Bx0jWq~becd)&F_E3u3&sC)L}ODB;Yws`=pXjN4qH{2h+N=6G&{b@*sx@6i(Gp!j^4K("
    "*M=q^Lg*Q?=jB7(XSXf=dgL~QysI1HU;K>?FI)!h&#z@ahx3>F8@5rU=$DR(;;Ub9yZ0vl@$?B)V7>}@eIV+i_~C3id$!!c%_g)rd|4|T!5t>ZRX3uL#To*s"
    "G}t9~wdx<51}r!H!3~Kh%9?S%0R9ms(Pp?JLVtb~8Z(v?E2pzxzWvabOCnN_+T1O+`40T3M!x^0+3<nXF8*WV5gxLsFCG&~;xzQd{(hg5sQl!E`;t_Z{5l+k"
    "D>fPf+Kv4XV9x597#r>_^jEy>5n-jeJBxR`R*+AhaZ97nCcLEAE0&q78Pf45PmAJz1{oCdxVy&PvFiF+^*M|)fJc~@{hclRQ4g$Ts3D93r>B8^))pW@(JX<G"
    "fZiR2lIkdm>!nylhfoV_ZfW6PM;3nVjqtXdn~v!Da}hpfY^wM%bJ#OtHT+rxqwQe>(L8Gs@<#o9>B>WoRN;UU2s-N%-d2XSOS5~A%x3i?M<Yl>WTlo!kS|=J"
    "(uvG?C)*ExOTc|;`-cW+v2}NfW&8$f>^X;$&)u~C*WkrEtZ&51)=kbmgXabL(7sYxENdtzvzfoJX+Bc_{ZU^?>25M2&?0aP_i;;meiVD{8#Nd&!v<{pL~Krk"
    "BSN3}?|q8FQ+Zemu^e-dBhRB;$;c^jVk!8_Qt)?N0UE(WZG<=lBruL(&rabz@-<C2#A^<%VKO!Js>tKXlUZf`yoz-DtcK%m!LGsww@Ul$e>V?<2I-2;fhuX{"
    "DgXpJsiznHiNzK(6n$%m(Ezx15iI}#dY98e+}M5$6eANp!FsNlLl7<7P|NC`IRl??q}iPtaIsO0q+#^Q&i)t#NvRl<-D-G!1FHkIi`awq-x`yHJ<1pepS1NM"
    "e@-LSGH<Y0u=|k1N(~JlbcT2~hRkAM^i7cbvE^y55GCSFR@)}P{VO6=YzEQb=L%_*!vLto0fI$i)r80WWf;j7>;*HA*FVz{<zq^HoO}*+r<Zc9#(`TCYYK-~"
    "={ljRj6^jL7N^}da>9<%ls#?M8nVaPHJZetYhBt1F(!eZ3GrHI2P)LBNe9`s21xBk->|PE+b`*PN;@P+Mb?QS1k-q6qzw}zwqnzr1o76?u{#z1uBu)2Z_z>_"
    "(jvL$DtSYjgawKx==P&-cSGyvC+>0=@9QqoIw^c_;ft=_^voTrp5yFPp)z;?lesN$w>R2jU<iaOxWG@lCR*TQ3C8&bYE=l+lPQ!lAnK)YZalYou+8pJN>(98"
    "fv`q}w_C~eV{5%PKkOw?)!z{c1MN>0_DEF4z-)gVR}bY9CN=Xi_~{ROv3v1blDD(Mg{Iq6Q7egqY>`*~>;DZFtVV@|vj6}"
)


def _seed_data() -> dict[str, list[dict[str, object]]]:
    return json.loads(gzip.decompress(base64.b85decode(_SEED_DATA)).decode())


def _seed_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_SEED_NAMESPACE, "/".join(parts))


def upgrade() -> None:
    op.create_table(
        "suggestion_category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=False),
        sa.Column("tooltip", sa.String(length=4000), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("locale", "key", name="uq_suggestion_category_locale_key"),
    )
    op.create_index(
        "ix_suggestion_category_locale", "suggestion_category", ["locale"], unique=False
    )
    op.create_table(
        "prompt_suggestion",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=4000), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], ["auth_user.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["suggestion_category.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category_id", "text", name="uq_prompt_suggestion_category_text"
        ),
    )
    op.create_index(
        "ix_prompt_suggestion_category_id",
        "prompt_suggestion",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        "ix_prompt_suggestion_archived_at",
        "prompt_suggestion",
        ["archived_at"],
        unique=False,
    )

    categories = []
    suggestions = []
    for locale, localized_categories in _seed_data().items():
        keys = _CATEGORY_KEYS[locale]
        if len(keys) != len(localized_categories):
            raise RuntimeError(
                f"Seed data for {locale} has {len(localized_categories)} categories "
                f"but {len(keys)} keys are declared"
            )
        for order, category in enumerate(localized_categories):
            key = keys[order]
            category_id = _seed_id("category", locale, key)
            categories.append(
                {
                    "id": category_id,
                    "locale": locale,
                    "key": key,
                    "title": category["title"],
                    "description": category["description"],
                    "icon": category["icon"],
                    "tooltip": category.get("tooltip"),
                    "display_order": order,
                }
            )
            for prompt_order, text in enumerate(category["suggestions"]):
                suggestions.append(
                    {
                        "id": _seed_id("suggestion", locale, key, str(prompt_order)),
                        "category_id": category_id,
                        "text": text,
                        "created_at": _SEED_TIMESTAMP,
                        "updated_at": _SEED_TIMESTAMP,
                        "created_by": None,
                        "archived_at": None,
                        "archived_by": None,
                    }
                )

    category_table = sa.table(
        "suggestion_category",
        sa.column("id", sa.Uuid()),
        sa.column("locale", sa.String()),
        sa.column("key", sa.String()),
        sa.column("title", sa.String()),
        sa.column("description", sa.String()),
        sa.column("icon", sa.String()),
        sa.column("tooltip", sa.String()),
        sa.column("display_order", sa.Integer()),
    )
    suggestion_table = sa.table(
        "prompt_suggestion",
        sa.column("id", sa.Uuid()),
        sa.column("category_id", sa.Uuid()),
        sa.column("text", sa.String()),
        sa.column("created_at", postgresql.TIMESTAMP()),
        sa.column("updated_at", postgresql.TIMESTAMP()),
        sa.column("created_by", sa.Uuid()),
        sa.column("archived_at", postgresql.TIMESTAMP()),
        sa.column("archived_by", sa.Uuid()),
    )
    op.bulk_insert(category_table, categories)
    op.bulk_insert(suggestion_table, suggestions)


def downgrade() -> None:
    op.drop_index("ix_prompt_suggestion_archived_at", table_name="prompt_suggestion")
    op.drop_index("ix_prompt_suggestion_category_id", table_name="prompt_suggestion")
    op.drop_table("prompt_suggestion")
    op.drop_index("ix_suggestion_category_locale", table_name="suggestion_category")
    op.drop_table("suggestion_category")
