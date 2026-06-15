# Model extès de hotspots criminals amb policia, risc i resposta institucional

## 1. Objectiu

Aquest document descriu una extensió del model de hotspots criminals de Short et al. L'objectiu és passar d'un model purament autoorganitzat, on el crim reforça l'atractivitat criminal, a un model de física social amb heterogeneïtat urbana i resposta institucional.

El model extès introdueix quatre idees:

- els barris poden tenir recompenses diferents;
- els barris poden tenir nivells de seguretat diferents;
- la policia pot reduir la utilitat criminal o capturar criminals;
- la policia pot respondre a crims observats, no necessàriament al risc latent real.

Aquest model és més ric, però també més difícil d'interpretar. Per això s'ha d'entendre com un marc general, no com la primera implementació obligatòria.

---

## 2. Model base

En el model original, cada cel·la espacial $$s$$ té una atractivitat total:

$$
A_s(t)=A_0+B_s(t)
$$

on:

- $$A_0$$ és l'atractivitat basal homogènia;
- $$B_s(t)$$ és l'atractivitat dinàmica generada pels crims previs;
- $$A_s(t)$$ és el camp que guia els criminals.

Un criminal situat a la cel·la $$s$$ comet crim amb probabilitat:

$$
p_{\text{crime}}(s,t)=1-e^{-A_s(t)\Delta t}
$$

Quan hi ha crim, el camp dinàmic augmenta localment:

$$
B_s(t+\Delta t) \sim B_s(t)+\theta E_s(t)
$$

on $$E_s(t)$$ és el nombre de crims reals comesos a la cel·la $$s$$ durant aquell pas temporal.

El mecanisme essencial és el feedback positiu:

$$
E_s \uparrow \rightarrow B_s \uparrow \rightarrow A_s \uparrow \rightarrow p_{\text{crime}} \uparrow \rightarrow E_s \uparrow
$$

Aquest feedback és el que genera hotspots criminals.

---

## 3. Per què cal separar conceptes?

El camp $$A_s(t)$$ del model base barreja conceptes socials diferents:

- valor econòmic d'una zona;
- facilitat o dificultat de robar-hi;
- seguretat privada;
- presència policial;
- memòria criminal;
- crim real;
- crim observat.

Per estudiar policia i desigualtat urbana, convé separar aquests ingredients.

Definim:

$$
R_s = \text{recompensa o oportunitat basal}
$$

$$
S_s = \text{seguretat o dificultat basal}
$$

$$
B_s(t) = \text{memòria criminal dinàmica}
$$

$$
P_s(t) = \text{pressió policial}
$$

$$
U_s(t) = \text{utilitat criminal efectiva}
$$

---

## 4. Utilitat criminal efectiva

La idea central és que els criminals no responen només al benefici brut, sinó a una relació benefici-risc. Per això proposem:

$$
U_s(t)=\frac{R_s+B_s(t)}{1+\alpha S_s+\chi P_s(t)}
$$

on:

- $$R_s$$ és el benefici potencial de robar a la cel·la $$s$$;
- $$B_s(t)$$ és la memòria criminal acumulada;
- $$S_s$$ és la seguretat basal;
- $$P_s(t)$$ és la pressió policial;
- $$\alpha$$ controla el pes de la seguretat;
- $$\chi$$ controla el pes dissuasiu de la policia.

Aquesta expressió s'interpreta com:

$$
\text{utilitat criminal}=\frac{\text{benefici percebut}}{\text{risc o dificultat percebuda}}
$$

La probabilitat de crim passa a ser:

$$
p_{\text{crime}}(s,t)=1-e^{-U_s(t)\Delta t}
$$

I el moviment dels criminals també hauria d'estar guiat per $$U_s(t)$$. Això vol dir que els criminals no es mouen cap al lloc més ric, sinó cap al lloc amb millor relació benefici-risc.

---

## 5. Heterogeneïtat urbana

Podem representar barris amb diferents recompenses:

$$
R_{\text{pobre}} < R_{\text{intermedi}} < R_{\text{ric}}
$$

Això modela que els barris rics poden ser més atractius perquè tenen més valor potencial.

Però també poden tenir més seguretat:

$$
S_{\text{pobre}} < S_{\text{intermedi}} < S_{\text{ric}}
$$

Això fa que el màxim de crim no hagi d'aparèixer necessàriament al barri ric. Pot aparèixer on el quocient benefici-risc és més alt:

$$
U_s \propto \frac{R_s}{1+\alpha S_s}
$$

Per això les zones intermèdies poden ser especialment importants: poden tenir prou recompensa i no tanta seguretat.

---

## 6. Policia com a camp

La policia es modela com un camp espacial:

$$
P_s(t)
$$

Aquest camp representa pressió policial, patrullatge, vigilància institucional o capacitat de resposta. No cal interpretar-lo com el nombre exacte de policies a cada cel·la, sinó com una intensitat agregada de control.

La policia pot tenir dos efectes.

### 6.1 Dissuasió

La policia redueix la utilitat criminal:

$$
U_s(t)=\frac{R_s+B_s(t)}{1+\alpha S_s+\chi P_s(t)}
$$

Si $$P_s(t)$$ augmenta, el denominador augmenta i la utilitat baixa.

### 6.2 Captura

La policia també pot capturar criminals:

$$
p_{\text{catch}}(s,t)=1-e^{-\kappa P_s(t)\Delta t}
$$

on $$\kappa$$ és l'eficiència de captura. Si un criminal és capturat, desapareix sense incrementar $$B_s(t)$$.

En una primera implementació, convé no activar captura i dissuasió alhora, perquè si el crim baixa no sabríem quin mecanisme ho causa.

---

## 7. Crim real, crim observat i policia

Una versió realista hauria de distingir:

$$
E_s(t)=\text{crims reals}
$$

$$
O_s(t)=\text{crims observats o reportats}
$$

$$
P_s(t)=\text{resposta policial}
$$

La policia no observa directament el camp latent $$B_s(t)$$. Observa crims, denúncies, trucades o registres. Per això podem escriure:

$$
O_s(t)\sim \text{Binomial}(E_s(t),q_s)
$$

on $$q_s$$ és la probabilitat que un crim sigui observat o denunciat.

Aquesta capa permet estudiar biaixos d'observació, però no és necessària per començar.

---

## 8. Memòria institucional

La policia no respon només al crim instantani. Respon a patrons recents. Per això es pot definir una memòria institucional:

$$
M_s(t+\Delta t)=\left(1-\frac{\Delta t}{\tau_M}\right)M_s(t)+O_s(t)
$$

on $$\tau_M$$ és el temps característic de memòria.

Si $$\tau_M$$ és petit, la policia respon a crims molt recents. Si és gran, conserva memòria de patrons antics.

---

## 9. Dinàmica del camp policial

Una possible dinàmica és:

$$
P_s(t+\Delta t)=P_s(t)+\Delta t[-\mu_P P_s(t)+\lambda_P M_s(t)]
$$

on:

- $$\mu_P$$ és la relaxació o retirada de policia;
- $$\lambda_P$$ és la força de resposta al crim observat recent;
- $$M_s(t)$$ és la memòria institucional.

Aquesta equació diu que la policia augmenta on hi ha memòria de crim observat i decau on aquesta memòria desapareix.

---

## 10. Recursos policials limitats

És essencial limitar els recursos policials:

$$
\sum_s P_s(t)=P_{\text{total}}
$$

Sense aquesta restricció, si hi ha molt crim, el model pot generar cada vegada més policia. Això podria portar a:

$$
P_s(t)\rightarrow \infty
$$

$$
U_s(t)\rightarrow 0
$$

$$
p_{\text{catch}}(s,t)\rightarrow 1
$$

i eliminar artificialment el crim. Amb recursos limitats, la policia només es redistribueix: més policia en una zona implica menys policia relativa en una altra.

---

## 11. Dues postures sobre com ha d'evolucionar la policia

### Postura A: policia reactiva als crims $$E_s(t)$$

Una opció és fer que la policia respongui als crims:

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{E}_s(t)
$$

on:

$$
\widetilde{E}_s(t)=\frac{E_s(t)}{\sum_r E_r(t)}
$$

Aquesta postura és més realista causalment. La policia real no veu l'atractivitat latent; veu incidents, denúncies o crims registrats.

Avantatges:

- és institucionalment interpretable;
- permet estudiar diferència entre crim real i crim observat;
- permet afegir biaixos de reporting.

Inconvenients:

- $$E_s(t)$$ és molt sorollós;
- pot fer que $$P_s(t)$$ sigui massa irregular;
- sovint requereix una memòria addicional $$M_s(t)$$.

### Postura B: policia orientada al camp $$B_s(t)$$

Una altra opció és fer que la policia respongui al camp dinàmic:

$$
P_s(t+\Delta t)=(1-\epsilon)P_s(t)+\epsilon \widetilde{B}_s(t)
$$

on:

$$
\widetilde{B}_s(t)=\frac{B_s(t)}{\sum_r B_r(t)}
$$

Aquesta postura és més física i més minimalista. El camp $$B_s(t)$$ ja és una memòria espacial del crim. Si la pregunta és què passa quan la policia intenta seguir hotspots, és natural que respongui a $$B_s(t)$$.

Avantatges:

- és suau i estable;
- evita introduir una memòria institucional separada;
- redueix el nombre de paràmetres;
- és ideal per estudiar camps acoblats $$B$$ i $$P$$.

Inconvenient principal:

- $$B_s(t)$$ és latent. Cal interpretar-lo com una estimació institucional del risc acumulat, no com una variable observada literalment.

---

## 12. Per què el model extès pot ser problemàtic

El model extès pot arribar a tenir molts paràmetres:

$$
\alpha,\chi,\kappa,\mu_P,\lambda_P,\tau_M,P_{\text{total}},q_s
$$

Això dificulta la interpretació. Si apareix una oscil·lació, pot ser causada per moltes coses diferents.

Per això el model extès és útil com a marc conceptual, però no és la millor primera implementació.

---

## 13. Règims esperats

El model extès pot generar:

- hotspots fixos;
- hotspots desplaçats;
- hotspots en zones intermèdies;
- fragmentació;
- oscil·lacions espacials;
- supressió parcial;
- eliminació artificial del crim si la policia no és limitada;
- divergència entre crim real i crim observat.

---

## 14. Recomanació

El model extès s'hauria d'entendre com el marc general. La implementació hauria de ser incremental:

1. model base;
2. recompensa heterogènia $$R_s$$;
3. policia reduïda que respon a $$B_s(t)$$;
4. comparació amb policia reactiva a $$E_s(t)$$;
5. seguretat basal $$S_s$$;
6. captura;
7. observació parcial.

Això manté la filosofia física: començar amb un model mínim i afegir mecanismes només quan siguin necessaris.
