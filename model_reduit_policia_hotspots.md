# Model reduït de hotspots criminals amb policia com a camp de control

## 1. Motivació

El model extès és conceptualment ric, però introdueix massa mecanismes i massa paràmetres. Per estudiar el fenomen de manera clara, convé construir un model reduït.

L'objectiu del model reduït és capturar el mecanisme essencial:

$$
\text{hotspot criminal} \rightarrow \text{resposta policial} \rightarrow \text{reducció de la utilitat} \rightarrow \text{desplaçament o supressió del hotspot}
$$

El model reduït només afegeix dos ingredients al model base:

1. recompensa urbana heterogènia $$R_s$$;
2. policia com a camp normalitzat $$P_s(t)$$.

---

## 2. Del model base a la recompensa heterogènia

En el model original:

$$
A_s(t)=A_0+B_s(t)
$$

on $$A_0$$ és constant i $$B_s(t)$$ és la memòria criminal.

En el model reduït substituïm $$A_0$$ per un camp de recompensa:

$$
R_s
$$

Així, sense policia, el camp que guia els criminals seria:

$$
A_s(t)=R_s+B_s(t)
$$

Això permet representar barris diferents:

$$
R_{\text{pobre}}<R_{\text{intermedi}}<R_{\text{ric}}
$$

El camp $$R_s$$ representa el benefici potencial de robar una zona en absència de control policial.

---

## 3. Policia com a camp normalitzat

Introduïm un camp policial:

$$
P_s(t)
$$

Aquest camp representa la distribució espacial relativa dels recursos policials.

Imposem:

$$
\sum_s P_s(t)=1
$$

Això significa que $$P_s(t)$$ no és una quantitat absoluta de policia, sinó una distribució relativa. Si augmenta en una zona, disminueix relativament en altres.

Aquesta normalització evita crear policia infinita i fa que el model sigui més físic.

---

## 4. Utilitat criminal efectiva

La utilitat que guia els criminals és:

$$
U_s(t)=\frac{R_s+B_s(t)}{1+C P_s(t)}
$$

on:

- $R_s$ és la recompensa basal;
- $B_s(t)$ és la memòria criminal;
- $P_s(t)$ és el camp policial;
- $C$ és la força total del control policial.

Aquesta expressió representa una relació benefici-risc:

$$
U_s(t)=\frac{\text{benefici percebut}}{\text{control percebut}}
$$

El numerador $$R_s+B_s(t)$$ és el benefici criminal percebut. El denominador $$1+C P_s(t)$$ és el risc o fricció institucional.

---

## 5. Probabilitat de crim

La probabilitat de crim és:

$$
p_{\text{crime}}(s,t)=1-e^{-U_s(t)\Delta t}
$$

Aquesta expressió conserva l'estructura del model original. L'únic canvi és que l'atractivitat original $$A_s(t)$$ és substituïda per la utilitat efectiva $$U_s(t)$$.

Si la policia augmenta en una zona, $$P_s(t)$$ puja, $$U_s(t)$$ baixa i la probabilitat de crim disminueix.

---

## 6. Moviment dels criminals

El moviment dels criminals també s'hauria de fer segons $$U_s(t)$$.

Això és important: els criminals no només roben menys en zones amb policia, sinó que també haurien de tendir a evitar zones on la relació benefici-risc és baixa.

Per tant, en el codi, allà on el model base usava $$A_s(t)$$, el model reduït hauria d'usar $$U_s(t)$$.

---

## 7. Dinàmica del camp policial

La qüestió central és com evoluciona $$P_s(t)$$. Hi ha dues postures defensables.

---

## 8. Postura A: policia reactiva als crims $$E_s(t)$$

La primera opció és:

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{E}_s(t)
$$

on:

$$
\widetilde{E}_s(t)=\frac{E_s(t)}{\sum_r E_r(t)}
$$

si hi ha crims en aquell pas temporal.

Després es normalitza:

$$
\sum_s P_s(t+\Delta t)=1
$$

### Interpretació

Aquesta versió diu que la policia respon als crims recents. És una policia reactiva.

### Defensa

Aquesta postura és més realista causalment. La policia real no observa el camp latent $$B_s(t)$$; observa incidents, denúncies, trucades o registres. Per tant, és natural que la resposta institucional provingui de $$E_s(t)$$ o d'una versió observada $$O_s(t)$$.

### Problema

El camp $$E_s(t)$$ és discret i sorollós. Pot haver-hi pocs crims en cada pas temporal, i això fa que la policia canviï de manera erràtica. Per això sovint cal suavitzar $$E_s(t)$$ o introduir una memòria.

---

## 9. Postura B: policia orientada al camp $$B_s(t)$$

La segona opció és:

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{B}_s(t)
$$

on:

$$
\widetilde{B}_s(t)=\frac{B_s(t)}{\sum_r B_r(t)}
$$

Després es normalitza:

$$
\sum_s P_s(t+\Delta t)=1
$$

### Interpretació

Aquesta versió diu que la policia respon al camp de risc acumulat o hotspot, no al crim instantani.

### Defensa

Aquesta postura és més física i més minimalista. El camp $$B_s(t)$$ ja és una memòria espacial i temporal del crim. Si la pregunta és què passa quan un camp de control intenta seguir els hotspots, llavors és natural que $$P_s(t)$$ evolucioni cap a $$B_s(t)$$.

També evita introduir una memòria policial addicional. El camp $$B_s(t)$$ ja conté persistència temporal.

### Problema

$$B_s(t)$$ és una variable latent del model. La policia real no l'observa literalment. Per tant, cal interpretar $$B_s(t)$$ com una estimació institucional del risc acumulat, no com una variable directament observada.

---

## 10. Elecció recomanada

Per al model reduït principal, usarem la postura B:

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{B}_s(t)
$$

perquè:

1. redueix el nombre de paràmetres;
2. evita introduir una memòria institucional separada;
3. produeix un camp policial més suau;
4. manté el model com un sistema de camps acoblats;
5. permet estudiar directament la competència entre hotspot criminal i control policial.

La postura A, basada en $$E_s(t)$$, s'hauria d'usar com a comparació o test de robustesa.

---

## 11. Paràmetres del model reduït

El model reduït introdueix només dos paràmetres nous importants:

$$
C
$$

i:

$$
\epsilon
$$

### Força de control $$C$$

Apareix a:

$$
U_s(t)=\frac{R_s+B_s(t)}{1+C P_s(t)}
$$

Si $$C=0$$, la policia no té efecte. Si $$C$$ és gran, la policia redueix molt la utilitat de les zones vigilades.

### Velocitat de resposta $$\epsilon$$

Apareix a:

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{B}_s(t)
$$

Si $$\epsilon$$ és petit, la policia canvia lentament. Si és gran, segueix ràpidament els hotspots.

A nivell físic:

$$
C=\text{intensitat del feedback negatiu}
$$

$$
\epsilon=\text{escala temporal del feedback negatiu}
$$

---

## 12. Sistema dinàmic reduït complet

El model reduït queda:

$$
U_s(t)=\frac{R_s+B_s(t)}{1+C P_s(t)}
$$

$$
p_{\text{crime}}(s,t)=1-e^{-U_s(t)\Delta t}
$$

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{B}_s(t)
$$

$$
\widetilde{B}_s(t)=\frac{B_s(t)}{\sum_r B_r(t)}
$$

$$
\sum_s P_s(t)=1
$$

amb la dinàmica original de $$B_s(t)$$:

$$
B_s(t+\Delta t)=\text{decay/diffusion}(B_s(t))+\theta E_s(t)
$$

Això és un sistema de dos camps acoblats:

- $$B_s(t)$$: camp criminal auto-reforçat;
- $$P_s(t)$$: camp policial de control.

---

## 13. Feedbacks del model

### Feedback positiu criminal

$$
E_s \uparrow \rightarrow B_s \uparrow \rightarrow U_s \uparrow \rightarrow E_s \uparrow
$$

Aquest feedback genera hotspots.

### Feedback negatiu policial

$$
B_s \uparrow \rightarrow P_s \uparrow \rightarrow U_s \downarrow \rightarrow E_s \downarrow
$$

Aquest feedback intenta suprimir o desplaçar hotspots.

La competència entre aquests dos mecanismes és el centre del model.

---

## 14. Interpretació física

El model reduït és un sistema de camps acoblats amb agents criminals.

El camp $$B_s(t)$$ genera autoorganització criminal. El camp $$P_s(t)$$ actua com un control redistributiu que intenta reduir la utilitat on el risc és alt.

La pregunta física és:

$$
\text{Quins règims emergeixen quan un camp auto-reforçat és perseguit per un camp de control?}
$$

---

## 15. Règims esperats

En funció de $$C$$ i $$\epsilon$$, poden aparèixer diferents règims.

### Control feble

Si $$C$$ és petit, el model s'assembla al model base i els hotspots persisteixen.

### Control fort i ràpid

Si $$C$$ i $$\epsilon$$ són grans, la policia segueix ràpidament els hotspots i pot suprimir-los localment.

### Control fort però lent

Si $$C$$ és gran però $$\epsilon$$ és petit, la policia arriba tard. Això pot generar desplaçament, persecució o oscil·lacions.

### Control intermedi

Pot aparèixer fragmentació: un hotspot gran es divideix en diversos hotspots petits.

---

## 16. Diagrama de fases conceptual

El model reduït permet explorar un espai de paràmetres bidimensional:

$$
(C,\epsilon)
$$

Això permet estudiar règims de manera clara:

- hotspot fix;
- hotspot desplaçat;
- hotspot oscil·lant;
- hotspot fragmentat;
- hotspot suprimit.

Aquesta és una estratègia molt pròpia de física estadística: no es tracta de calibrar cada paràmetre amb precisió, sinó d'entendre canvis qualitatius de règim.

---

## 17. Diagnòstics recomanats

Per analitzar el model, cal mesurar:

- nombre total de crims;
- intensitat del hotspot;
- desviació espacial de $$B_s(t)$$;
- desviació espacial de $$P_s(t)$$;
- correlació entre $$B_s(t)$$ i $$P_s(t)$$;
- activitat per barri;
- centre de massa del crim;
- centre de massa de $$B_s(t)$$;
- centre de massa de $$P_s(t)$$.

Per exemple:

$$
x_B(t)=\frac{\sum_s x_s B_s(t)}{\sum_s B_s(t)}
$$

$$
x_P(t)=\frac{\sum_s x_s P_s(t)}{\sum_s P_s(t)}
$$

Si $$x_B(t)$$ i $$x_P(t)$$ oscil·len amb retard, això indicaria una dinàmica de persecució entre hotspot i policia.

---

## 18. Per què aquest model és un bon primer pas

Aquest model és útil perquè:

1. manté la interpretabilitat;
2. només afegeix dos paràmetres nous;
3. conserva l'estructura del model base;
4. permet estudiar feedback positiu i negatiu;
5. evita ajustar massa mecanismes alhora;
6. facilita construir un diagrama de règims.

És prou simple per entendre'l i prou ric per generar resultats nous.

---

## 19. Extensions futures

Un cop entès el model reduït, es poden afegir altres capes.

### Seguretat basal

$$
U_s(t)=\frac{R_s+B_s(t)}{1+\alpha S_s+C P_s(t)}
$$

### Captura

$$
p_{\text{catch}}(s,t)=1-e^{-\kappa P_s(t)\Delta t}
$$

### Crim observat

$$
O_s(t)\sim \text{Binomial}(E_s(t),q_s)
$$

### Policia basada en crims observats

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{O}_s(t)
$$

Aquestes extensions són interessants, però no necessàries per a la primera anàlisi.

---

## 20. Conclusió

El model reduït proposat és:

$$
U_s(t)=\frac{R_s+B_s(t)}{1+C P_s(t)}
$$

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{B}_s(t)
$$

amb:

$$
\sum_s P_s(t)=1
$$

Aquest model representa una policia que segueix el camp de hotspots i redueix la utilitat criminal local. És una extensió mínima i física del model base.

La seva força és que permet estudiar clarament la competència entre:

$$
\text{auto-reforç criminal}
$$

i:

$$
\text{control institucional}
$$

amb només dos paràmetres nous:

$$
C,\epsilon
$$

Per això és el millor punt de partida abans d'afegir mecanismes socials més realistes però més difícils d'interpretar.
