"""Deterministic localized rendering for Ask Dashboard answers.

Routing and calculations stay language-neutral/internal. This module translates only
user-facing Markdown after a structured answer has already been calculated. Player
names, alliance names, score values, intent names, and analytics codes are never
translated or sent to a second model.
"""

from __future__ import annotations

import re
from string import Formatter

from ._legacy import legacy
from ._routing import (
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
    SCORE_DERIVED_INTENTS,
    is_obvious_smalltalk_question,
)

SUPPORTED_LOCALIZED_ANSWER_LOCALES = ("es", "fr", "vi", "id")

LOCALIZED_RENDERED_INTENTS = {
    "alliance_exclusion_total_net",
    "net_vs_positive_ranking",
    "player_exclusion_impact",
    "negative_share_change",
    "top_contributors",
    "net_score_leader_summary",
    "alliance_score_overview",
    "player_net_score_leader",
    "dashboard_help",
    "dashboard_limitation",
    "unsupported_question",
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
}


ANSWER_TEXT = {
    "es": {
        "period_suffix": " para **{period}**",
        "scope_full": "En todo el servidor{period}",
        "scope_filters": "Con los filtros actuales de la barra lateral{period}",
        "scope_named": " dentro de **{names}**",
        "missing_calculation": "Este cálculo no puede completarse porque faltan estas columnas en los datos actuales: {columns}.",
        "missing_explanation": "Esta explicación no puede completarse porque faltan estas columnas en los datos actuales: {columns}.",
        "empty_score_scope": "No hay datos de puntuación en el ámbito de filtros actual. Selecciona al menos una alianza y una opción de estado neto y vuelve a intentarlo.",
        "empty_player_scope": "No hay datos de puntuación de jugadores en el ámbito de filtros actual. Selecciona al menos una alianza y una opción de estado neto y vuelve a intentarlo.",
        "requires_multiple_alliances": "Esta comparación necesita al menos dos alianzas en el ámbito de filtros actual. Selecciona más alianzas y vuelve a intentarlo.",
        "requires_both_negative": "Esta pregunta compara los lados positivo y negativo, pero el filtro Estado neto actual no incluye tanto Positivo como Negativo. Selecciona ambos estados y vuelve a intentarlo.",
        "requires_both_general": "Esta pregunta compara la contribución positiva con el impacto negativo, pero el filtro Estado neto actual no incluye tanto Positivo como Negativo. Selecciona ambos estados para obtener la explicación completa.",
        "missing_alliance_available": "Entendí que quieres calcular la puntuación neta total después de excluir una alianza, pero no pude identificar su nombre. Las alianzas disponibles para este período SVS son: **{available}**.",
        "missing_alliance_example": "Entendí que quieres excluir una alianza, pero no pude identificar su nombre. Incluye el nombre de una alianza en la pregunta; por ejemplo: **What is the total net score without TDA?**",
        "outside_player": "Reconocí {names}, pero no está incluida en el filtro de alianzas actual. Añádela en la barra lateral y vuelve a preguntar.",
        "outside_exclusion": "{names} no está incluida en el filtro de alianzas actual, por lo que excluirla no cambia la puntuación neta total actual de **{before_net}**. Añade primero la alianza a la selección de la barra lateral si quieres una comparación antes y después.",
        "tied_net": "Los filtros actuales producen un empate en el primer puesto de puntuación neta total: {names}, con {score} cada una. Como no hay una única alianza líder, la premisa de esta pregunta no se aplica actualmente.",
        "no_positive_server": "No hay ninguna puntuación neta positiva de jugador disponible para todo el servidor en este período SVS.",
        "no_positive_filters": "No hay ninguna puntuación neta positiva de jugador disponible con los filtros actuales de la barra lateral.",
        "unsupported_smalltalk": "¡Hola! Ask Dashboard está listo para ayudarte con los datos SVS registrados. Prueba a preguntar por la puntuación o clasificación de un jugador o alianza, contribuciones, exclusiones o la definición de una métrica.",
        "unsupported_prediction": "Ask Dashboard analiza puntuaciones SVS registradas, por lo que no puede predecir un ganador futuro ni el resultado del próximo SVS. Puede resumir clasificaciones, contribuciones, pérdidas, exclusiones y líderes por puntuación neta a partir de los datos disponibles.",
        "unsupported_generic": "No pude relacionar esa pregunta con uno de los análisis admitidos por el panel. Pregunta por puntuaciones registradas de jugadores o alianzas, clasificaciones, exclusiones, contribución positiva, impacto negativo o definiciones de métricas.\n\n**Ejemplos de preguntas (escríbelas en inglés):**\n- What is net score?\n- Which player has the strongest overall balance?\n- What is the total net score without TDA?\n- Who contributed most in SnS?\n- Why did the negative share rise?",
        "metric_net": "**Puntuación neta** = **puntos obtenidos − puntos perdidos**. Una puntuación neta positiva significa que el jugador o la alianza obtuvo más puntos de los que perdió; una negativa significa que las pérdidas fueron mayores. Ask Dashboard usa la puntuación neta como medida predeterminada del resultado general registrado.",
        "metric_gained": "**Puntos obtenidos** es el total de puntos SVS registrados como ganados. Mide la actividad que añadió puntos, pero no resta los puntos perdidos, por lo que no equivale a la puntuación neta.",
        "metric_lost": "**Puntos perdidos** es la magnitud total de los puntos SVS registrados como perdidos. Ask Dashboard la muestra como una cantidad positiva de pérdida y la resta de los puntos obtenidos al calcular la puntuación neta.",
        "metric_positive": "**Contribución positiva** es la suma de las **puntuaciones netas positivas de los jugadores** en el ámbito seleccionado. Solo cuenta a los jugadores cuya puntuación neta es superior a cero; no es simplemente el total de puntos obtenidos.",
        "metric_negative": "**Impacto negativo** es el total absoluto de las **puntuaciones netas negativas de los jugadores** en el ámbito seleccionado. Muestra cuánto redujo el resultado el lado negativo y presenta la magnitud como un valor positivo fácil de comparar.",
        "metric_negative_share": "**Participación negativa** = **impacto negativo ÷ (contribución positiva + impacto negativo) × 100**. Describe la proporción del lado negativo dentro de la magnitud total de puntuación neta, no el porcentaje de jugadores que terminaron en negativo.",
        "alliance_positive_tie": "{intro}, {names} empatan con la mayor contribución positiva, con **{score}** cada una.",
        "alliance_positive_single": "{intro}, **{alliance}** es la alianza que más contribuyó al lado positivo, con **{score}**.",
        "positive_share": "Generó **{share:.1f}%** de la contribución positiva en este ámbito.",
        "positive_ranking": "**Clasificación por contribución positiva**",
        "player_positive_tie": "{intro}{scope}, {names} empatan con la mayor contribución positiva, con **{score}** cada uno.",
        "player_positive_single": "{intro}{scope}, **{player}** fue quien más contribuyó al lado positivo, con **{score}**.",
        "label_alliance": "Alianza",
        "label_score_gained": "Puntos obtenidos",
        "label_score_lost": "Puntos perdidos",
        "label_net_score": "Puntuación neta",
        "label_positive_contribution": "Contribución positiva",
        "label_negative_impact": "Impacto negativo",
        "label_total_net": "Puntuación neta total",
        "label_share_positive": "Participación en la contribución positiva de este ámbito",
        "player_net_tie": "{intro}{scope}, {names} empatan en el primer puesto por puntuación neta de jugador con **{score}**.",
        "player_net_single": "{intro}{scope}, **{player}** tiene la puntuación neta más alta entre los jugadores, con **{score}**.",
        "player_ranking_named": "**Mejores jugadores de {names} por puntuación neta**",
        "player_ranking_filters": "**Mejores jugadores por puntuación neta con los filtros actuales**",
        "player_boundary_named": "Esta clasificación solo compara jugadores dentro de **{names}**. No compara la puntuación neta total de {names} con la de otras alianzas.",
        "player_boundary_filters": "Esta es una clasificación de jugadores con los filtros activos; no identifica qué alianza tiene la mayor puntuación neta combinada.",
        "alliance_net_tie": "{intro}, {names} empatan en el primer puesto de puntuación neta total con **{score}**.",
        "alliance_net_single": "{intro}, **{alliance}** lidera la puntuación neta total con **{score}**.",
        "alliance_net_ranking": "**Clasificación de alianzas por puntuación neta — filtros actuales**",
        "alliance_net_note": "Aquí solo se clasifica la puntuación neta total de cada alianza. La posición por contribución positiva es una métrica distinta y no forma parte de esta lista.",
        "overview_intro": "La palabra puntuación puede referirse a varias métricas. Con los filtros actuales de la barra lateral{period}:",
        "overview_overall": "Líder general por puntuación neta",
        "overview_gained": "Mayor cantidad de puntos obtenidos",
        "overview_lost": "Menor cantidad de puntos perdidos",
        "overview_positive": "Mayor contribución positiva",
        "tie_note": " (empate)",
        "overview_note": "Para una pregunta general sobre el rendimiento de una alianza, Ask Dashboard usa la puntuación neta como medida predeterminada. Indica una métrica como puntos obtenidos, puntos perdidos, puntuación neta o contribución positiva cuando quieras una clasificación concreta.",
        "alliance_exclusion_intro": "Con los filtros actuales del panel{period}, excluir {alliances} cambia la puntuación neta total de **{before}** a **{after}** (**{change}**).",
        "excluded_group": "El grupo de alianzas excluido aportó:",
        "players_remaining": "Jugadores restantes: **{after}/{before}**.",
        "exclusion_interpret_negative": "El total mejora porque el grupo de alianzas excluido tenía una contribución neta negativa en este ámbito.",
        "exclusion_interpret_positive": "El total disminuye porque el grupo de alianzas excluido tenía una contribución neta positiva en este ámbito.",
        "exclusion_interpret_zero": "El total no cambia porque el grupo de alianzas excluido tenía una contribución neta de cero en este ámbito.",
        "outside_note": "Las siguientes alianzas mencionadas ya estaban fuera del filtro actual y, por tanto, no tuvieron un efecto adicional: {names}.",
        "net_positive_premise": "La premisa no coincide con los datos filtrados actuales{period}. **{alliance}** ocupa el primer puesto tanto en puntuación neta total ({net}) como en contribución positiva ({positive}).",
        "rank_second": "segundo lugar",
        "rank_not_second": "el puesto #{rank}, no el segundo",
        "net_positive_main": "Con los filtros actuales de la barra lateral{period}, **{top}** ocupa el primer puesto en puntuación neta total con **{top_net}**, mientras que ocupa {rank_statement} en contribución positiva con **{top_positive}**.",
        "net_positive_detail": "**{leader}** lidera la contribución positiva con **{leader_positive}**, **{gap}** más que {top}. Sin embargo, el impacto negativo de {leader} es **{leader_negative}**, frente a **{top_negative}** de {top}. Esto da a {top} una ventaja de **{advantage}** por perder menos puntos.",
        "net_positive_conclusion": "El menor impacto negativo compensa la menor contribución positiva y deja a {top} por delante de {leader} en **{lead}** de puntuación neta total. Aquí, la contribución positiva es la suma de las puntuaciones netas positivas de los jugadores y la puntuación neta total equivale a contribución positiva menos impacto negativo.",
        "exclusion_none": "No hay jugadores excluidos actualmente del grupo filtrado{period}. Por tanto, los resultados antes y después son idénticos: **{players} jugadores** con una puntuación neta total de **{net}**. Elimina al menos un jugador en la pestaña Análisis de selección de jugadores para comparar el impacto.",
        "exclusion_intro": "Después de las exclusiones actuales{period}, el análisis incluye **{after} de {before} jugadores**. **Excluidos:** {excluded}.",
        "outcome_improved": "La puntuación neta total **mejoró en {amount}**. Las exclusiones eliminaron **{negative}** de impacto negativo, pero solo **{positive}** de contribución positiva, por lo que la reducción de pérdidas fue mayor que la reducción de aportes positivos.",
        "outcome_decreased": "La puntuación neta total **disminuyó en {amount}**. Las exclusiones eliminaron **{positive}** de contribución positiva, pero solo **{negative}** de impacto negativo, por lo que se retiró más aporte útil que impacto perjudicial.",
        "outcome_unchanged": "La puntuación neta total no cambió. La contribución positiva eliminada (**{positive}**) y el impacto negativo eliminado (**{negative}**) se compensaron exactamente.",
        "negative_no_magnitude": "No se puede calcular el porcentaje negativo porque el grupo filtrado actual no tiene magnitud de puntuación neta positiva ni negativa.",
        "negative_none": "No hay jugadores excluidos actualmente del grupo filtrado{period}. La participación negativa permanece en **{share:.1f}%**. Elimina al menos un jugador en la pestaña Análisis de selección de jugadores para crear una comparación antes y después.",
        "negative_after_none": "Después de las exclusiones actuales{period}, no queda magnitud de puntuación en el grupo seleccionado, por lo que no se puede calcular el porcentaje negativo posterior a la exclusión.",
        "negative_mismatch": "La premisa no coincide con la selección actual: la participación negativa",
        "negative_normal": "La participación negativa",
        "negative_increased": "{prefix} **aumentó {change:.1f} puntos porcentuales**, de **{before:.1f}%** a **{after:.1f}%**.",
        "negative_decreased": "{prefix} **disminuyó {change:.1f} puntos porcentuales**, de **{before:.1f}%** a **{after:.1f}%**.",
        "negative_unchanged": "{prefix} se mantuvo prácticamente sin cambios en **{after:.1f}%** ({change:+.1f} puntos porcentuales).",
        "negative_reason_increase_down": "Esto ocurrió porque las exclusiones eliminaron una proporción mayor de contribución positiva que de impacto negativo. La contribución positiva cayó **{positive_rate:.1f}%**, mientras que el impacto negativo cayó **{negative_rate:.1f}%**. Aunque el impacto negativo bruto también disminuyó, pasó a representar una proporción mayor de un total restante más pequeño.",
        "negative_reason_increase_same": "Esto ocurrió porque las exclusiones eliminaron una proporción mayor de contribución positiva que de impacto negativo. La contribución positiva cayó **{positive_rate:.1f}%**, mientras que el impacto negativo cayó **{negative_rate:.1f}%**. El impacto negativo bruto no aumentó; se mantuvo igual, pero pasó a representar una proporción mayor de un total restante más pequeño.",
        "negative_reason_decrease": "Las exclusiones eliminaron una proporción mayor de impacto negativo que de contribución positiva. El impacto negativo cayó **{negative_rate:.1f}%**, mientras que la contribución positiva cayó **{positive_rate:.1f}%**.",
        "negative_reason_unchanged": "La contribución positiva y el impacto negativo cambiaron casi en la misma proporción, por lo que el equilibrio entre ambos lados se mantuvo estable.",
        "negative_intro": "Después de excluir **{count} jugador(es)**{period} — **{excluded}** — {direction}",
        "removed": "eliminado {amount}, {rate:.1f}%",
        "negative_formula": "Porcentaje negativo = impacto negativo ÷ (contribución positiva + impacto negativo).",
        "top_single_intro": "Los principales contribuyentes{period} se ordenan por **puntuación neta de jugador**.",
        "top_multi_intro": "Como hay **{count} alianzas** seleccionadas{period}, el panel muestra los **{top_n}** principales contribuyentes de cada alianza. Los jugadores se ordenan por **puntuación neta de jugador**.",
        "top_group_positive": "contribuyentes positivos por puntuación neta",
        "top_group_no_positive": "jugadores con las puntuaciones netas más altas; ningún jugador tiene puntuación neta positiva en este ámbito",
        "top_player_detail": "neto **{net}** (obtenidos {gained}, perdidos {lost})",
        "top_player_share": ", **{share:.1f}%** de la contribución positiva de la alianza",
        "top_group_share": "Los jugadores mostrados representan **{share:.1f}%** de la contribución positiva de esta alianza en el ámbito de filtros actual.",
        "alliance_total": "Puntuación neta total de la alianza en este ámbito: **{net}**.",
        "excluded_others": "y {count} más",
        "help_text": "## Cómo usar Ask Dashboard\n\n1. Selecciona primero el período SVS y los filtros de la barra lateral.\n2. Pregunta por puntuaciones de jugadores o alianzas, clasificaciones, exclusiones o contribución negativa.\n3. Las respuestas usan únicamente los datos incluidos por los filtros actuales.\n\nLas áreas admitidas incluyen resúmenes generales de puntuación de alianzas, líderes de puntuación neta de jugadores y alianzas, contribución positiva frente a impacto negativo, exclusiones de jugadores, cambios en la participación negativa, principales contribuyentes y puntuación neta total tras excluir alianzas concretas.\n\n**Ejemplos de preguntas (escríbelas en inglés):**\n- Top net score player\n- Top alliance score\n- Which alliance leads net score?\n- Who contributed most in SnS?\n- What changed after excluding the selected players?\n\n**Más ayuda (usa los comandos en inglés):** `help filters`, `help questions`, `help player selection` o `help limitations`.\n\nAsk Dashboard describe resultados de puntuación registrados. No puede determinar los motivos, intenciones, carácter, habilidad, estrategia, responsabilidad ni circunstancias de juego no registradas de un jugador a partir de los datos de puntuación.",
        "limitation_text": "Ask Dashboard no puede determinar el comportamiento, la intención, el motivo, el carácter, la habilidad, la estrategia, la responsabilidad ni las circunstancias de juego no registradas de un jugador a partir de los datos de puntuación.\n\nPuede describir resultados registrados con los filtros actuales, como puntos obtenidos, puntos perdidos, puntuación neta, clasificaciones y totales de contribución. Un mismo resultado de puntuación puede surgir de situaciones distintas que no aparecen en este conjunto de datos.\n\nEn su lugar, puedes preguntar por los puntos obtenidos, los puntos perdidos, la puntuación neta o la clasificación registrada del jugador en el ámbito actual.",
        "rounded_notice": "Nota sobre los datos: algunos valores de puntos obtenidos de este período se basan en la visualización redondeada de Evony dentro del juego. Por ello, los totales, las puntuaciones netas, las clasificaciones y los resultados derivados son aproximados y pueden diferir ligeramente de los valores exactos."
    },
    "fr": {
        "period_suffix": " pour **{period}**",
        "scope_full": "Sur l’ensemble du serveur{period}",
        "scope_filters": "Avec les filtres actuels de la barre latérale{period}",
        "scope_named": " au sein de **{names}**",
        "missing_calculation": "Ce calcul ne peut pas être effectué car les données actuelles ne contiennent pas les colonnes suivantes : {columns}.",
        "missing_explanation": "Cette explication ne peut pas être fournie car les données actuelles ne contiennent pas les colonnes suivantes : {columns}.",
        "empty_score_scope": "Aucune donnée de score n’est disponible dans le périmètre de filtres actuel. Sélectionnez au moins une alliance et une option de statut net, puis réessayez.",
        "empty_player_scope": "Aucune donnée de score de joueur n’est disponible dans le périmètre de filtres actuel. Sélectionnez au moins une alliance et une option de statut net, puis réessayez.",
        "requires_multiple_alliances": "Cette comparaison nécessite au moins deux alliances dans le périmètre de filtres actuel. Sélectionnez davantage d’alliances et réessayez.",
        "requires_both_negative": "Cette question compare les côtés positif et négatif, mais le filtre Statut net actuel n’inclut pas à la fois Positif et Négatif. Sélectionnez les deux statuts et réessayez.",
        "requires_both_general": "Cette question compare la contribution positive à l’impact négatif, mais le filtre Statut net actuel n’inclut pas à la fois Positif et Négatif. Sélectionnez les deux statuts pour obtenir l’explication complète.",
        "missing_alliance_available": "J’ai compris que vous souhaitez calculer le score net total après exclusion d’une alliance, mais je n’ai pas pu identifier son nom. Les alliances disponibles pour cette période SVS sont : **{available}**.",
        "missing_alliance_example": "J’ai compris que vous souhaitez exclure une alliance, mais je n’ai pas pu identifier son nom. Incluez le nom d’une alliance dans la question, par exemple : **What is the total net score without TDA?**",
        "outside_player": "J’ai reconnu {names}, mais cette alliance n’est pas incluse dans le filtre d’alliances actuel. Ajoutez-la dans la barre latérale, puis reposez la question.",
        "outside_exclusion": "{names} n’est pas incluse dans le filtre d’alliances actuel ; son exclusion ne modifie donc pas le score net total actuel de **{before_net}**. Ajoutez d’abord l’alliance à la sélection de la barre latérale si vous souhaitez une comparaison avant/après.",
        "tied_net": "Les filtres actuels produisent une égalité à la première place du score net total : {names}, avec {score} chacune. Comme aucune alliance n’est seule en tête, la prémisse de cette question ne s’applique pas actuellement.",
        "no_positive_server": "Aucun score net positif de joueur n’est disponible pour l’ensemble du serveur pendant cette période SVS.",
        "no_positive_filters": "Aucun score net positif de joueur n’est disponible avec les filtres actuels de la barre latérale.",
        "unsupported_smalltalk": "Bonjour ! Ask Dashboard est prêt à vous aider avec les données SVS enregistrées. Essayez une question sur le score ou le classement d’un joueur ou d’une alliance, les contributions, les exclusions ou la définition d’une métrique.",
        "unsupported_prediction": "Ask Dashboard analyse les scores SVS enregistrés ; il ne peut donc pas prédire un futur vainqueur ni le résultat du prochain SVS. Il peut résumer les classements, contributions, pertes, exclusions et leaders au score net à partir des données disponibles.",
        "unsupported_generic": "Je n’ai pas pu associer cette question à l’une des analyses prises en charge par le tableau de bord. Posez une question sur les scores enregistrés des joueurs ou alliances, les classements, les exclusions, la contribution positive, l’impact négatif ou les définitions de métriques.\n\n**Exemples de questions (à saisir en anglais) :**\n- What is net score?\n- Which player has the strongest overall balance?\n- What is the total net score without TDA?\n- Who contributed most in SnS?\n- Why did the negative share rise?",
        "metric_net": "**Score net** = **points gagnés − points perdus**. Un score net positif signifie que le joueur ou l’alliance a gagné plus de points qu’il ou elle n’en a perdu ; une valeur négative signifie que les pertes sont supérieures aux gains. Ask Dashboard utilise le score net comme mesure par défaut du résultat global enregistré.",
        "metric_gained": "**Points gagnés** correspond au nombre total de points SVS enregistrés comme obtenus. Cette mesure indique l’activité ayant ajouté des points, mais ne soustrait pas les points perdus ; elle n’est donc pas équivalente au score net.",
        "metric_lost": "**Points perdus** correspond au total des points SVS enregistrés comme perdus. Ask Dashboard les affiche comme une quantité positive de pertes et les soustrait aux points gagnés lors du calcul du score net.",
        "metric_positive": "**Contribution positive** est la somme des **scores nets positifs des joueurs** dans le périmètre sélectionné. Seuls les joueurs dont le score net est supérieur à zéro sont comptés ; il ne s’agit pas simplement du total des points gagnés.",
        "metric_negative": "**Impact négatif** est la valeur absolue totale des **scores nets négatifs des joueurs** dans le périmètre sélectionné. Il indique de combien le côté négatif réduit le résultat, tout en présentant cette valeur sous forme positive pour faciliter la comparaison.",
        "metric_negative_share": "**Part négative** = **impact négatif ÷ (contribution positive + impact négatif) × 100**. Elle indique la part de l’impact négatif dans l’ensemble formé par la contribution positive et l’impact négatif, et non le pourcentage de joueurs ayant terminé avec un score négatif.",
        "alliance_positive_tie": "{intro}, {names} sont à égalité pour la plus grande contribution positive, avec **{score}** chacune.",
        "alliance_positive_single": "{intro}, **{alliance}** est l’alliance qui apporte la plus forte contribution positive, avec **{score}**.",
        "positive_share": "Elle génère **{share:.1f}%** de la contribution positive dans ce périmètre.",
        "positive_ranking": "**Classement par contribution positive**",
        "player_positive_tie": "{intro}{scope}, {names} sont à égalité pour la plus grande contribution positive, avec **{score}** chacun.",
        "player_positive_single": "{intro}{scope}, **{player}** est le joueur qui apporte la plus forte contribution positive, avec **{score}**.",
        "label_alliance": "Alliance",
        "label_score_gained": "Points gagnés",
        "label_score_lost": "Points perdus",
        "label_net_score": "Score net",
        "label_positive_contribution": "Contribution positive",
        "label_negative_impact": "Impact négatif",
        "label_total_net": "Score net total",
        "label_share_positive": "Part de la contribution positive dans ce périmètre",
        "player_net_tie": "{intro}{scope}, {names} sont à égalité à la première place du score net des joueurs avec **{score}**.",
        "player_net_single": "{intro}{scope}, **{player}** possède le score net le plus élevé parmi les joueurs, avec **{score}**.",
        "player_ranking_named": "**Meilleurs joueurs de {names} par score net**",
        "player_ranking_filters": "**Meilleurs joueurs par score net avec les filtres actuels**",
        "player_boundary_named": "Ce classement compare uniquement les joueurs de **{names}**. Il ne compare pas le score net total de {names} à celui des autres alliances.",
        "player_boundary_filters": "Il s’agit d’un classement de joueurs avec les filtres actifs ; il n’indique pas quelle alliance possède le score net combiné le plus élevé.",
        "alliance_net_tie": "{intro}, {names} sont à égalité à la première place du score net total avec **{score}**.",
        "alliance_net_single": "{intro}, **{alliance}** est en tête du score net total avec **{score}**.",
        "alliance_net_ranking": "**Classement des alliances par score net — filtres actuels**",
        "alliance_net_note": "Seul le score net total des alliances est classé ici. Le rang en contribution positive est une métrique distincte et ne fait pas partie de cette liste.",
        "overview_intro": "Le terme score peut désigner plusieurs métriques. Avec les filtres actuels de la barre latérale{period} :",
        "overview_overall": "Leader global par score net",
        "overview_gained": "Plus grand nombre de points gagnés",
        "overview_lost": "Plus faible nombre de points perdus",
        "overview_positive": "Contribution positive la plus élevée",
        "tie_note": " (égalité)",
        "overview_note": "Pour une question générale sur les performances d’une alliance, Ask Dashboard utilise le score net comme mesure par défaut. Précisez une métrique comme les points gagnés, les points perdus, le score net ou la contribution positive si vous souhaitez un classement spécifique.",
        "alliance_exclusion_intro": "Avec les filtres actuels du tableau de bord{period}, l’exclusion de {alliances} fait passer le score net total de **{before}** à **{after}** (**{change}**).",
        "excluded_group": "Le groupe d’alliances exclu a contribué comme suit :",
        "players_remaining": "Joueurs restants : **{after}/{before}**.",
        "exclusion_interpret_negative": "Le total s’améliore parce que le groupe d’alliances exclu avait une contribution nette négative dans ce périmètre.",
        "exclusion_interpret_positive": "Le total diminue parce que le groupe d’alliances exclu avait une contribution nette positive dans ce périmètre.",
        "exclusion_interpret_zero": "Le total ne change pas parce que le groupe d’alliances exclu avait une contribution nette nulle dans ce périmètre.",
        "outside_note": "Les alliances suivantes étaient déjà hors du filtre actuel et n’ont donc eu aucun effet supplémentaire : {names}.",
        "net_positive_premise": "La prémisse ne correspond pas aux données filtrées actuelles{period}. **{alliance}** est première à la fois en score net total ({net}) et en contribution positive ({positive}).",
        "rank_second": "deuxième",
        "rank_not_second": "#{rank}, et non deuxième",
        "net_positive_main": "Avec les filtres actuels de la barre latérale{period}, **{top}** est première au score net total avec **{top_net}**, tandis qu’elle est {rank_statement} en contribution positive avec **{top_positive}**.",
        "net_positive_detail": "**{leader}** mène la contribution positive avec **{leader_positive}**, soit **{gap}** de plus que {top}. Cependant, l’impact négatif de {leader} est de **{leader_negative}**, contre **{top_negative}** pour {top}. {top} bénéficie ainsi d’un avantage de **{advantage}** grâce à des pertes plus faibles.",
        "net_positive_conclusion": "L’impact négatif plus faible compense la contribution positive plus petite et laisse {top} devant {leader} de **{lead}** au score net total. Ici, la contribution positive correspond à la somme des scores nets positifs des joueurs et le score net total est égal à la contribution positive moins l’impact négatif.",
        "exclusion_none": "Aucun joueur n’est actuellement exclu du groupe filtré{period}. Les résultats avant et après sont donc identiques : **{players} joueurs** avec un score net total de **{net}**. Retirez au moins un joueur dans l’onglet Analyse de la sélection des joueurs pour comparer l’impact.",
        "exclusion_intro": "Après les exclusions actuelles{period}, l’analyse comprend **{after} joueurs sur {before}**. **Exclus :** {excluded}.",
        "outcome_improved": "Le score net total **s’est amélioré de {amount}**. Les exclusions ont réduit l’impact négatif de **{negative}** mais la contribution positive de seulement **{positive}** ; la diminution de l’impact négatif a donc été plus importante que celle de la contribution positive.",
        "outcome_decreased": "Le score net total **a diminué de {amount}**. Les exclusions ont réduit la contribution positive de **{positive}** mais l’impact négatif de seulement **{negative}** ; la diminution de la contribution positive a donc été plus importante que celle de l’impact négatif.",
        "outcome_unchanged": "Le score net total n’a pas changé. La contribution positive supprimée (**{positive}**) et l’impact négatif supprimé (**{negative}**) se compensent exactement.",
        "negative_no_magnitude": "La part négative ne peut pas être calculée car le groupe filtré actuel ne présente ni contribution positive ni impact négatif.",
        "negative_none": "Aucun joueur n’est actuellement exclu du groupe filtré{period}. La part négative reste inchangée à **{share:.1f}%**. Retirez au moins un joueur dans l’onglet Analyse de la sélection des joueurs pour créer une comparaison avant/après.",
        "negative_after_none": "Après les exclusions actuelles{period}, il ne reste ni contribution positive ni impact négatif dans le groupe sélectionné ; la part négative après exclusion ne peut donc pas être calculée.",
        "negative_mismatch": "La prémisse ne correspond pas à la sélection actuelle : la part négative",
        "negative_normal": "La part négative",
        "negative_increased": "{prefix} **a augmenté de {change:.1f} points de pourcentage**, passant de **{before:.1f}%** à **{after:.1f}%**.",
        "negative_decreased": "{prefix} **a diminué de {change:.1f} points de pourcentage**, passant de **{before:.1f}%** à **{after:.1f}%**.",
        "negative_unchanged": "{prefix} est pratiquement inchangée à **{after:.1f}%** ({change:+.1f} point(s) de pourcentage).",
        "negative_reason_increase_down": "Cela s’explique par le fait que les exclusions ont supprimé une proportion plus importante de contribution positive que d’impact négatif. La contribution positive a baissé de **{positive_rate:.1f}%**, tandis que l’impact négatif a baissé de **{negative_rate:.1f}%**. Même si l’impact négatif brut a lui aussi diminué, il représente désormais une plus grande part d’un total restant plus petit.",
        "negative_reason_increase_same": "Cela s’explique par le fait que les exclusions ont supprimé une proportion plus importante de contribution positive que d’impact négatif. La contribution positive a baissé de **{positive_rate:.1f}%**, tandis que l’impact négatif a baissé de **{negative_rate:.1f}%**. L’impact négatif brut n’a pas augmenté ; il est resté identique mais représente une plus grande part d’un total restant plus petit.",
        "negative_reason_decrease": "Les exclusions ont supprimé une proportion plus importante d’impact négatif que de contribution positive. L’impact négatif a baissé de **{negative_rate:.1f}%**, tandis que la contribution positive a baissé de **{positive_rate:.1f}%**.",
        "negative_reason_unchanged": "La contribution positive et l’impact négatif ont évolué dans des proportions presque identiques ; l’équilibre entre les deux côtés est donc resté stable.",
        "negative_intro": "Après l’exclusion de **{count} joueur(s)**{period} — **{excluded}** — {direction}",
        "removed": "supprimé : {amount}, {rate:.1f}%",
        "negative_formula": "Part négative = impact négatif ÷ (contribution positive + impact négatif).",
        "top_single_intro": "Les principaux contributeurs{period} sont classés selon le **score net des joueurs**.",
        "top_multi_intro": "Comme **{count} alliances** sont sélectionnées{period}, le tableau de bord affiche les **{top_n}** principaux contributeurs de chaque alliance. Les joueurs sont classés selon leur **score net**.",
        "top_group_positive": "contributeurs positifs par score net",
        "top_group_no_positive": "joueurs ayant les scores nets les plus élevés ; aucun joueur n’a de score net positif dans ce périmètre",
        "top_player_detail": "net **{net}** (gagnés {gained}, perdus {lost})",
        "top_player_share": ", **{share:.1f}%** de la contribution positive de l’alliance",
        "top_group_share": "Les joueurs affichés représentent **{share:.1f}%** de la contribution positive de cette alliance dans le périmètre de filtres actuel.",
        "alliance_total": "Score net total de l’alliance dans ce périmètre : **{net}**.",
        "excluded_others": "et {count} autres",
        "help_text": "## Comment utiliser Ask Dashboard\n\n1. Sélectionnez d’abord la période SVS et les filtres de la barre latérale.\n2. Posez une question sur les scores de joueurs ou d’alliances, les classements, les exclusions ou la contribution négative.\n3. Les réponses utilisent uniquement les données incluses par les filtres actuels.\n\nLes domaines pris en charge comprennent les résumés généraux des scores d’alliances, les leaders au score net des joueurs et des alliances, la contribution positive par rapport à l’impact négatif, les exclusions de joueurs, les variations de la part négative, les principaux contributeurs et le score net total après exclusion d’alliances nommées.\n\n**Exemples de questions (à saisir en anglais) :**\n- Top net score player\n- Top alliance score\n- Which alliance leads net score?\n- Who contributed most in SnS?\n- What changed after excluding the selected players?\n\n**Aide supplémentaire (utilisez les commandes en anglais) :** `help filters`, `help questions`, `help player selection` ou `help limitations`.\n\nAsk Dashboard décrit des résultats de score enregistrés. Il ne peut pas déduire les motivations, intentions, le caractère, les compétences, la stratégie, la responsabilité ou les circonstances de jeu non observées d’un joueur à partir des seuls scores.",
        "limitation_text": "Ask Dashboard ne peut pas déterminer le comportement, l’intention, la motivation, le caractère, les compétences, la stratégie, la responsabilité ou les circonstances de jeu non observées d’un joueur à partir des seuls scores.\n\nIl peut décrire des résultats enregistrés avec les filtres actuels, comme les points gagnés, les points perdus, le score net, les classements et les totaux de contribution. Un même résultat de score peut provenir de situations différentes qui ne sont pas enregistrées dans ce jeu de données.\n\nVous pouvez plutôt demander les points gagnés, les points perdus, le score net ou le classement enregistré du joueur dans le périmètre actuel.",
        "rounded_notice": "Note sur les données : certaines valeurs de points gagnés pour cette période reposent sur l’affichage arrondi d’Evony dans le jeu. Les totaux, scores nets, classements et résultats dérivés sont donc approximatifs et peuvent différer légèrement des valeurs exactes."
    },
    "vi": {
        "period_suffix": " trong kỳ **{period}**",
        "scope_full": "Trên toàn máy chủ{period}",
        "scope_filters": "Theo các bộ lọc hiện tại trên thanh bên{period}",
        "scope_named": " trong **{names}**",
        "missing_calculation": "Không thể hoàn tất phép tính này vì dữ liệu hiện tại thiếu các cột: {columns}.",
        "missing_explanation": "Không thể hoàn tất phần giải thích này vì dữ liệu hiện tại thiếu các cột: {columns}.",
        "empty_score_scope": "Không có dữ liệu điểm trong phạm vi bộ lọc hiện tại. Hãy chọn ít nhất một liên minh và một tùy chọn trạng thái ròng rồi thử lại.",
        "empty_player_scope": "Không có dữ liệu điểm của người chơi trong phạm vi bộ lọc hiện tại. Hãy chọn ít nhất một liên minh và một tùy chọn trạng thái ròng rồi thử lại.",
        "requires_multiple_alliances": "So sánh này cần ít nhất hai liên minh trong phạm vi bộ lọc hiện tại. Hãy chọn thêm liên minh rồi thử lại.",
        "requires_both_negative": "Câu hỏi này so sánh phía dương và phía âm, nhưng bộ lọc Trạng thái ròng hiện tại không bao gồm cả Dương và Âm. Hãy chọn cả hai trạng thái rồi thử lại.",
        "requires_both_general": "Câu hỏi này so sánh đóng góp tích cực với tác động tiêu cực, nhưng bộ lọc Trạng thái ròng hiện tại không bao gồm cả Dương và Âm. Hãy chọn cả hai trạng thái để có phần giải thích đầy đủ.",
        "missing_alliance_available": "Tôi hiểu rằng bạn muốn tính tổng điểm ròng sau khi loại một liên minh, nhưng tôi không xác định được tên liên minh. Các liên minh có sẵn trong kỳ SVS này là: **{available}**.",
        "missing_alliance_example": "Tôi hiểu rằng bạn muốn loại một liên minh, nhưng tôi không xác định được tên liên minh. Hãy đưa tên liên minh vào câu hỏi, ví dụ: **What is the total net score without TDA?**",
        "outside_player": "Tôi nhận ra {names}, nhưng liên minh này không nằm trong bộ lọc liên minh hiện tại. Hãy thêm liên minh đó ở thanh bên rồi hỏi lại.",
        "outside_exclusion": "{names} không nằm trong bộ lọc liên minh hiện tại, vì vậy việc loại liên minh này không làm thay đổi tổng điểm ròng hiện tại là **{before_net}**. Hãy thêm liên minh vào lựa chọn ở thanh bên trước nếu bạn muốn so sánh trước và sau.",
        "tied_net": "Các bộ lọc hiện tại tạo ra kết quả đồng hạng nhất về tổng điểm ròng: {names}, mỗi liên minh có {score}. Vì không có một liên minh duy nhất dẫn đầu, tiền đề của câu hỏi này hiện không áp dụng.",
        "no_positive_server": "Không có điểm ròng dương của người chơi trên toàn máy chủ trong kỳ SVS này.",
        "no_positive_filters": "Không có điểm ròng dương của người chơi theo các bộ lọc hiện tại trên thanh bên.",
        "unsupported_smalltalk": "Xin chào! Ask Dashboard sẵn sàng hỗ trợ bạn với dữ liệu SVS đã ghi nhận. Hãy thử hỏi về điểm hoặc xếp hạng của người chơi/liên minh, đóng góp, việc loại người chơi hoặc định nghĩa chỉ số.",
        "unsupported_prediction": "Ask Dashboard phân tích điểm SVS đã ghi nhận nên không thể dự đoán người thắng trong tương lai hoặc kết quả SVS tiếp theo. Công cụ có thể tóm tắt xếp hạng, đóng góp, điểm bị mất, việc loại người chơi và người dẫn đầu về điểm ròng từ dữ liệu hiện có.",
        "unsupported_generic": "Tôi không thể khớp câu hỏi đó với một phân tích được hỗ trợ trên bảng điều khiển. Hãy hỏi về điểm đã ghi nhận của người chơi hoặc liên minh, xếp hạng, việc loại người chơi, đóng góp tích cực, tác động tiêu cực hoặc định nghĩa chỉ số.\n\n**Ví dụ câu hỏi (hãy nhập bằng tiếng Anh):**\n- What is net score?\n- Which player has the strongest overall balance?\n- What is the total net score without TDA?\n- Who contributed most in SnS?\n- Why did the negative share rise?",
        "metric_net": "**Điểm ròng** = **điểm kiếm được − điểm bị mất**. Điểm ròng dương nghĩa là người chơi hoặc liên minh kiếm được nhiều điểm hơn số điểm bị mất; giá trị âm nghĩa là số điểm bị mất lớn hơn. Ask Dashboard dùng điểm ròng làm thước đo mặc định cho kết quả tổng thể đã ghi nhận.",
        "metric_gained": "**Điểm kiếm được** là tổng số điểm SVS được ghi nhận là đã kiếm được. Chỉ số này đo hoạt động tạo thêm điểm nhưng không trừ điểm bị mất, vì vậy không giống điểm ròng.",
        "metric_lost": "**Điểm bị mất** là tổng số điểm SVS được ghi nhận là đã mất. Ask Dashboard hiển thị số điểm bị mất dưới dạng một giá trị dương và trừ giá trị này khỏi điểm kiếm được khi tính điểm ròng.",
        "metric_positive": "**Đóng góp tích cực** là tổng **điểm ròng dương của người chơi** trong phạm vi đã chọn. Chỉ những người chơi có điểm ròng lớn hơn 0 được tính; đây không đơn giản là tổng điểm kiếm được.",
        "metric_negative": "**Tác động tiêu cực** là tổng trị tuyệt đối của **điểm ròng âm của người chơi** trong phạm vi đã chọn. Chỉ số này cho biết phần điểm ròng âm làm giảm kết quả bao nhiêu, đồng thời hiển thị giá trị đó dưới dạng số dương để dễ so sánh.",
        "metric_negative_share": "**Tỷ trọng tiêu cực** = **tác động tiêu cực ÷ (đóng góp tích cực + tác động tiêu cực) × 100**. Chỉ số này cho biết tác động tiêu cực chiếm bao nhiêu trong tổng của đóng góp tích cực và tác động tiêu cực, không phải tỷ lệ người chơi có điểm ròng âm.",
        "alliance_positive_tie": "{intro}, {names} đồng hạng về đóng góp tích cực lớn nhất với **{score}** mỗi liên minh.",
        "alliance_positive_single": "{intro}, **{alliance}** là liên minh có đóng góp tích cực lớn nhất, với **{score}**.",
        "positive_share": "Liên minh này chiếm **{share:.1f}%** trong tổng đóng góp tích cực của phạm vi này.",
        "positive_ranking": "**Xếp hạng đóng góp tích cực**",
        "player_positive_tie": "{intro}{scope}, {names} đồng hạng về đóng góp tích cực lớn nhất với **{score}** mỗi người.",
        "player_positive_single": "{intro}{scope}, **{player}** là người có đóng góp tích cực lớn nhất, với **{score}**.",
        "label_alliance": "Liên minh",
        "label_score_gained": "Điểm kiếm được",
        "label_score_lost": "Điểm bị mất",
        "label_net_score": "Điểm ròng",
        "label_positive_contribution": "Đóng góp tích cực",
        "label_negative_impact": "Tác động tiêu cực",
        "label_total_net": "Tổng điểm ròng",
        "label_share_positive": "Tỷ trọng trong tổng đóng góp tích cực của phạm vi này",
        "player_net_tie": "{intro}{scope}, {names} đồng hạng nhất về điểm ròng của người chơi với **{score}**.",
        "player_net_single": "{intro}{scope}, **{player}** có điểm ròng cao nhất trong số người chơi với **{score}**.",
        "player_ranking_named": "**Người chơi hàng đầu trong {names} theo điểm ròng**",
        "player_ranking_filters": "**Người chơi hàng đầu theo điểm ròng với bộ lọc hiện tại**",
        "player_boundary_named": "Xếp hạng này chỉ so sánh người chơi trong **{names}**. Nó không so sánh tổng điểm ròng của {names} với các liên minh khác.",
        "player_boundary_filters": "Đây là xếp hạng người chơi theo các bộ lọc đang hoạt động; nó không xác định liên minh nào có tổng điểm ròng kết hợp cao nhất.",
        "alliance_net_tie": "{intro}, {names} đồng hạng nhất về tổng điểm ròng với **{score}**.",
        "alliance_net_single": "{intro}, **{alliance}** dẫn đầu về tổng điểm ròng với **{score}**.",
        "alliance_net_ranking": "**Xếp hạng liên minh theo điểm ròng — bộ lọc hiện tại**",
        "alliance_net_note": "Ở đây chỉ xếp hạng tổng điểm ròng của liên minh. Xếp hạng đóng góp tích cực là một chỉ số riêng và không nằm trong danh sách này.",
        "overview_intro": "Từ “điểm” có thể chỉ nhiều chỉ số khác nhau. Theo các bộ lọc hiện tại trên thanh bên{period}:",
        "overview_overall": "Dẫn đầu tổng thể theo điểm ròng",
        "overview_gained": "Điểm kiếm được cao nhất",
        "overview_lost": "Điểm bị mất thấp nhất",
        "overview_positive": "Đóng góp tích cực cao nhất",
        "tie_note": " (đồng hạng)",
        "overview_note": "Đối với câu hỏi chung về hiệu suất liên minh, Ask Dashboard dùng điểm ròng làm thước đo mặc định. Hãy nêu rõ chỉ số như điểm kiếm được, điểm bị mất, điểm ròng hoặc đóng góp tích cực khi bạn muốn một bảng xếp hạng cụ thể.",
        "alliance_exclusion_intro": "Theo các bộ lọc hiện tại của bảng điều khiển{period}, việc loại {alliances} làm tổng điểm ròng thay đổi từ **{before}** thành **{after}** (**{change}**).",
        "excluded_group": "Nhóm liên minh bị loại có kết quả:",
        "players_remaining": "Người chơi còn lại: **{after}/{before}**.",
        "exclusion_interpret_negative": "Tổng điểm được cải thiện vì nhóm liên minh bị loại có đóng góp ròng âm trong phạm vi này.",
        "exclusion_interpret_positive": "Tổng điểm giảm vì nhóm liên minh bị loại có đóng góp ròng dương trong phạm vi này.",
        "exclusion_interpret_zero": "Tổng điểm không đổi vì nhóm liên minh bị loại có đóng góp ròng bằng 0 trong phạm vi này.",
        "outside_note": "Các liên minh được nhắc đến sau đây vốn đã nằm ngoài bộ lọc hiện tại nên không tạo thêm ảnh hưởng: {names}.",
        "net_positive_premise": "Tiền đề không khớp với dữ liệu đã lọc hiện tại{period}. **{alliance}** đứng thứ nhất cả về tổng điểm ròng ({net}) và đóng góp tích cực ({positive}).",
        "rank_second": "thứ hai",
        "rank_not_second": "hạng #{rank}, không phải thứ hai",
        "net_positive_main": "Theo các bộ lọc hiện tại trên thanh bên{period}, **{top}** đứng thứ nhất về tổng điểm ròng với **{top_net}**, trong khi đứng {rank_statement} về đóng góp tích cực với **{top_positive}**.",
        "net_positive_detail": "**{leader}** dẫn đầu về đóng góp tích cực với **{leader_positive}**, nhiều hơn {top} **{gap}**. Tuy nhiên, tác động tiêu cực của {leader} là **{leader_negative}**, so với **{top_negative}** của {top}. Điều này giúp {top} có lợi thế **{advantage}** nhờ mất ít điểm hơn.",
        "net_positive_conclusion": "Tác động tiêu cực thấp hơn bù cho đóng góp tích cực nhỏ hơn, giúp {top} dẫn {leader} **{lead}** về tổng điểm ròng. Ở đây, đóng góp tích cực là tổng điểm ròng dương của người chơi và tổng điểm ròng bằng đóng góp tích cực trừ tác động tiêu cực.",
        "exclusion_none": "Hiện không có người chơi nào bị loại khỏi nhóm đã lọc{period}. Vì vậy kết quả trước và sau giống nhau: **{players} người chơi** với tổng điểm ròng **{net}**. Hãy bỏ chọn ít nhất một người chơi trong tab Phân tích lựa chọn người chơi để so sánh tác động.",
        "exclusion_intro": "Sau khi áp dụng lựa chọn loại người chơi hiện tại{period}, phân tích còn **{after}/{before} người chơi**. **Người chơi bị loại:** {excluded}.",
        "outcome_improved": "Tổng điểm ròng **tăng thêm {amount}**. Việc loại người chơi đã giảm tác động tiêu cực **{negative}** nhưng chỉ làm giảm đóng góp tích cực **{positive}**, nên tác động tiêu cực giảm nhiều hơn đóng góp tích cực.",
        "outcome_decreased": "Tổng điểm ròng **giảm {amount}**. Việc loại người chơi đã làm giảm đóng góp tích cực **{positive}** nhưng chỉ giảm tác động tiêu cực **{negative}**, nên đóng góp tích cực giảm nhiều hơn tác động tiêu cực.",
        "outcome_unchanged": "Tổng điểm ròng không thay đổi. Đóng góp tích cực bị loại (**{positive}**) và tác động tiêu cực bị loại (**{negative}**) bù trừ nhau chính xác.",
        "negative_no_magnitude": "Không thể tính tỷ trọng tiêu cực vì nhóm đã lọc hiện tại không có đóng góp tích cực hoặc tác động tiêu cực.",
        "negative_none": "Hiện không có người chơi nào bị loại khỏi nhóm đã lọc{period}. Tỷ trọng tiêu cực giữ nguyên ở **{share:.1f}%**. Hãy bỏ chọn ít nhất một người chơi trong tab Phân tích lựa chọn người chơi để tạo so sánh trước và sau.",
        "negative_after_none": "Sau khi áp dụng lựa chọn loại người chơi hiện tại{period}, nhóm được chọn không còn đóng góp tích cực hoặc tác động tiêu cực nên không thể tính tỷ trọng tiêu cực sau khi loại.",
        "negative_mismatch": "Tiền đề không khớp với lựa chọn hiện tại: tỷ trọng tiêu cực",
        "negative_normal": "Tỷ trọng tiêu cực",
        "negative_increased": "{prefix} **tăng {change:.1f} điểm phần trăm**, từ **{before:.1f}%** lên **{after:.1f}%**.",
        "negative_decreased": "{prefix} **giảm {change:.1f} điểm phần trăm**, từ **{before:.1f}%** xuống **{after:.1f}%**.",
        "negative_unchanged": "{prefix} gần như không đổi ở **{after:.1f}%** ({change:+.1f} điểm phần trăm).",
        "negative_reason_increase_down": "Điều này xảy ra vì việc loại người chơi làm giảm tỷ lệ đóng góp tích cực nhiều hơn tác động tiêu cực. Đóng góp tích cực giảm **{positive_rate:.1f}%**, trong khi tác động tiêu cực giảm **{negative_rate:.1f}%**. Mặc dù tác động tiêu cực tuyệt đối cũng giảm, nó lại chiếm tỷ trọng lớn hơn trong tổng còn lại nhỏ hơn.",
        "negative_reason_increase_same": "Điều này xảy ra vì việc loại người chơi làm giảm tỷ lệ đóng góp tích cực nhiều hơn tác động tiêu cực. Đóng góp tích cực giảm **{positive_rate:.1f}%**, trong khi tác động tiêu cực giảm **{negative_rate:.1f}%**. Tác động tiêu cực tuyệt đối không tăng; nó giữ nguyên nhưng chiếm tỷ trọng lớn hơn trong tổng còn lại nhỏ hơn.",
        "negative_reason_decrease": "Việc loại người chơi làm giảm tỷ lệ tác động tiêu cực nhiều hơn đóng góp tích cực. Tác động tiêu cực giảm **{negative_rate:.1f}%**, trong khi đóng góp tích cực giảm **{positive_rate:.1f}%**.",
        "negative_reason_unchanged": "Đóng góp tích cực và tác động tiêu cực thay đổi gần như cùng tỷ lệ, vì vậy cân bằng giữa hai phía vẫn ổn định.",
        "negative_intro": "Sau khi loại **{count} người chơi**{period} — **{excluded}** — {direction}",
        "removed": "đã loại {amount}, {rate:.1f}%",
        "negative_formula": "Tỷ trọng tiêu cực = tác động tiêu cực ÷ (đóng góp tích cực + tác động tiêu cực).",
        "top_single_intro": "Những người đóng góp hàng đầu{period} được xếp hạng theo **điểm ròng của người chơi**.",
        "top_multi_intro": "Vì có **{count} liên minh** được chọn{period}, bảng điều khiển hiển thị **{top_n}** người đóng góp hàng đầu trong mỗi liên minh. Người chơi được xếp hạng theo **điểm ròng của người chơi**.",
        "top_group_positive": "người đóng góp tích cực theo điểm ròng",
        "top_group_no_positive": "người chơi có điểm ròng cao nhất; không có người chơi nào có điểm ròng dương trong phạm vi này",
        "top_player_detail": "ròng **{net}** (kiếm được {gained}, bị mất {lost})",
        "top_player_share": ", **{share:.1f}%** đóng góp tích cực của liên minh",
        "top_group_share": "Những người chơi được liệt kê chiếm **{share:.1f}%** đóng góp tích cực của liên minh này trong phạm vi bộ lọc hiện tại.",
        "alliance_total": "Tổng điểm ròng của liên minh trong phạm vi này: **{net}**.",
        "excluded_others": "và {count} người khác",
        "help_text": "## Cách sử dụng Ask Dashboard\n\n1. Trước tiên hãy chọn kỳ SVS và các bộ lọc trên thanh bên.\n2. Hỏi về điểm của người chơi hoặc liên minh, xếp hạng, việc loại người chơi hoặc tác động tiêu cực.\n3. Câu trả lời chỉ sử dụng dữ liệu nằm trong các bộ lọc hiện tại.\n\nCác nội dung được hỗ trợ gồm tổng quan điểm của liên minh, người dẫn đầu về điểm ròng của người chơi và liên minh, đóng góp tích cực so với tác động tiêu cực, việc loại người chơi, thay đổi tỷ trọng tiêu cực, người đóng góp hàng đầu và tổng điểm ròng sau khi loại liên minh được nêu tên.\n\n**Ví dụ câu hỏi (hãy nhập bằng tiếng Anh):**\n- Top net score player\n- Top alliance score\n- Which alliance leads net score?\n- Who contributed most in SnS?\n- What changed after excluding the selected players?\n\n**Trợ giúp thêm (dùng lệnh tiếng Anh):** `help filters`, `help questions`, `help player selection` hoặc `help limitations`.\n\nAsk Dashboard mô tả kết quả điểm đã ghi nhận. Công cụ không thể xác định động cơ, ý định, tính cách, kỹ năng, chiến lược, trách nhiệm hoặc hoàn cảnh chơi không được ghi nhận của người chơi chỉ từ dữ liệu điểm.",
        "limitation_text": "Ask Dashboard không thể xác định hành vi, ý định, động cơ, tính cách, kỹ năng, chiến lược, trách nhiệm hoặc hoàn cảnh chơi không được ghi nhận của người chơi chỉ từ dữ liệu điểm.\n\nCông cụ có thể mô tả các kết quả đã ghi nhận theo bộ lọc hiện tại, chẳng hạn điểm kiếm được, điểm bị mất, điểm ròng, xếp hạng và tổng đóng góp. Cùng một kết quả điểm có thể phát sinh từ những tình huống khác nhau không được ghi lại trong bộ dữ liệu này.\n\nThay vào đó, bạn có thể hỏi về điểm kiếm được, điểm bị mất, điểm ròng hoặc xếp hạng đã ghi nhận của người chơi trong phạm vi hiện tại.",
        "rounded_notice": "Lưu ý về dữ liệu: một số giá trị điểm kiếm được trong kỳ này dựa trên các số đã được Evony làm tròn khi hiển thị trong trò chơi. Vì vậy, tổng điểm, điểm ròng, thứ hạng và các kết quả được tính từ những giá trị này chỉ mang tính xấp xỉ và có thể chênh lệch nhẹ so với giá trị chính xác."
    },
    "id": {
        "period_suffix": " untuk **{period}**",
        "scope_full": "Di seluruh server{period}",
        "scope_filters": "Dengan filter bilah sisi saat ini{period}",
        "scope_named": " di dalam **{names}**",
        "missing_calculation": "Perhitungan ini tidak dapat diselesaikan karena data saat ini tidak memiliki kolom: {columns}.",
        "missing_explanation": "Penjelasan ini tidak dapat diselesaikan karena data saat ini tidak memiliki kolom: {columns}.",
        "empty_score_scope": "Tidak ada data poin dalam cakupan filter saat ini. Pilih setidaknya satu aliansi dan satu opsi status bersih, lalu coba lagi.",
        "empty_player_scope": "Tidak ada data poin pemain dalam cakupan filter saat ini. Pilih setidaknya satu aliansi dan satu opsi status bersih, lalu coba lagi.",
        "requires_multiple_alliances": "Perbandingan ini membutuhkan setidaknya dua aliansi dalam cakupan filter saat ini. Pilih lebih banyak aliansi lalu coba lagi.",
        "requires_both_negative": "Pertanyaan ini membandingkan sisi positif dan negatif, tetapi filter Status Bersih saat ini tidak mencakup Positif dan Negatif sekaligus. Pilih kedua status lalu coba lagi.",
        "requires_both_general": "Pertanyaan ini membandingkan kontribusi positif dengan dampak negatif, tetapi filter Status Bersih saat ini tidak mencakup Positif dan Negatif sekaligus. Pilih kedua status untuk mendapatkan penjelasan lengkap.",
        "missing_alliance_available": "Saya memahami bahwa Anda ingin menghitung total poin bersih setelah mengecualikan sebuah aliansi, tetapi saya tidak dapat mengenali nama aliansinya. Nama aliansi yang tersedia untuk periode SVS ini adalah: **{available}**.",
        "missing_alliance_example": "Saya memahami bahwa Anda ingin mengecualikan sebuah aliansi, tetapi saya tidak dapat mengenali namanya. Sertakan nama aliansi dalam pertanyaan, misalnya: **What is the total net score without TDA?**",
        "outside_player": "Saya mengenali {names}, tetapi aliansi itu tidak termasuk dalam filter aliansi saat ini. Tambahkan aliansi tersebut di bilah sisi, lalu tanyakan lagi.",
        "outside_exclusion": "{names} tidak termasuk dalam filter aliansi saat ini, sehingga mengecualikannya tidak mengubah total poin bersih saat ini sebesar **{before_net}**. Tambahkan aliansi itu ke pilihan bilah sisi terlebih dahulu jika Anda ingin perbandingan sebelum dan sesudah.",
        "tied_net": "Filter saat ini menghasilkan hasil seri di peringkat pertama total poin bersih: {names}, masing-masing sebesar {score}. Karena tidak ada satu aliansi yang menjadi pemimpin tunggal, premis pertanyaan ini saat ini tidak berlaku.",
        "no_positive_server": "Tidak ada poin bersih positif pemain yang tersedia untuk seluruh server pada periode SVS ini.",
        "no_positive_filters": "Tidak ada poin bersih positif pemain yang tersedia dengan filter bilah sisi saat ini.",
        "unsupported_smalltalk": "Halo! Ask Dashboard siap membantu dengan data SVS yang tercatat. Coba tanyakan poin atau peringkat pemain/aliansi, kontribusi, pengecualian, atau definisi metrik.",
        "unsupported_prediction": "Ask Dashboard menganalisis poin SVS yang tercatat, sehingga tidak dapat memprediksi pemenang di masa depan atau hasil SVS berikutnya. Ask Dashboard dapat merangkum peringkat, kontribusi, poin yang hilang, pengecualian, dan pemimpin poin bersih dari data yang tersedia.",
        "unsupported_generic": "Saya tidak dapat mencocokkan pertanyaan itu dengan salah satu analisis yang didukung dasbor. Tanyakan tentang poin pemain atau aliansi yang tercatat, peringkat, pengecualian, kontribusi positif, dampak negatif, atau definisi metrik.\n\n**Contoh pertanyaan (ketik dalam bahasa Inggris):**\n- What is net score?\n- Which player has the strongest overall balance?\n- What is the total net score without TDA?\n- Who contributed most in SnS?\n- Why did the negative share rise?",
        "metric_net": "**Poin bersih** = **poin yang diperoleh − poin yang hilang**. Poin bersih positif berarti pemain atau aliansi memperoleh lebih banyak poin daripada yang hilang; nilai negatif berarti kehilangan lebih besar daripada perolehan. Ask Dashboard menggunakan poin bersih sebagai ukuran default untuk hasil keseluruhan yang tercatat.",
        "metric_gained": "**Poin yang diperoleh** adalah jumlah total poin SVS yang tercatat sebagai diperoleh. Metrik ini mengukur aktivitas yang menambah poin, tetapi tidak mengurangi poin yang hilang, sehingga tidak sama dengan poin bersih.",
        "metric_lost": "**Poin yang hilang** adalah total besarnya poin SVS yang tercatat sebagai hilang. Ask Dashboard menampilkannya sebagai jumlah kehilangan positif dan menguranginya dari poin yang diperoleh saat menghitung poin bersih.",
        "metric_positive": "**Kontribusi positif** adalah jumlah **poin bersih positif pemain** dalam cakupan yang dipilih. Hanya pemain dengan poin bersih di atas nol yang dihitung; ini bukan sekadar total poin yang diperoleh.",
        "metric_negative": "**Dampak negatif** adalah total absolut dari **poin bersih negatif pemain** dalam cakupan yang dipilih. Metrik ini menunjukkan seberapa besar sisi negatif mengurangi hasil sambil tetap menampilkan besarnya sebagai angka positif yang mudah dibandingkan.",
        "metric_negative_share": "**Persentase negatif** = **dampak negatif ÷ (kontribusi positif + dampak negatif) × 100**. Metrik ini menggambarkan porsi sisi negatif dari total besarnya poin bersih, bukan persentase pemain yang berakhir negatif.",
        "alliance_positive_tie": "{intro}, {names} seri untuk kontribusi positif terbesar dengan **{score}** masing-masing.",
        "alliance_positive_single": "{intro}, **{alliance}** adalah aliansi yang paling banyak berkontribusi pada sisi positif dengan **{score}**.",
        "positive_share": "Aliansi ini menghasilkan **{share:.1f}%** dari kontribusi positif dalam cakupan ini.",
        "positive_ranking": "**Peringkat kontribusi positif**",
        "player_positive_tie": "{intro}{scope}, {names} seri untuk kontribusi positif terbesar dengan **{score}** masing-masing.",
        "player_positive_single": "{intro}{scope}, **{player}** adalah pemain yang paling banyak berkontribusi pada sisi positif dengan **{score}**.",
        "label_alliance": "Aliansi",
        "label_score_gained": "Poin yang diperoleh",
        "label_score_lost": "Poin yang hilang",
        "label_net_score": "Poin bersih",
        "label_positive_contribution": "Kontribusi positif",
        "label_negative_impact": "Dampak negatif",
        "label_total_net": "Total poin bersih",
        "label_share_positive": "Persentase kontribusi positif dalam cakupan ini",
        "player_net_tie": "{intro}{scope}, {names} seri di peringkat pertama poin bersih pemain dengan **{score}**.",
        "player_net_single": "{intro}{scope}, **{player}** memiliki poin bersih tertinggi di antara pemain dengan **{score}**.",
        "player_ranking_named": "**Pemain teratas di {names} berdasarkan poin bersih**",
        "player_ranking_filters": "**Pemain teratas berdasarkan poin bersih dengan filter saat ini**",
        "player_boundary_named": "Peringkat ini hanya membandingkan pemain di dalam **{names}**. Peringkat ini tidak membandingkan total poin bersih {names} dengan aliansi lain.",
        "player_boundary_filters": "Ini adalah peringkat pemain berdasarkan filter aktif; ini tidak menentukan aliansi mana yang memiliki total poin bersih gabungan tertinggi.",
        "alliance_net_tie": "{intro}, {names} seri di peringkat pertama total poin bersih dengan **{score}**.",
        "alliance_net_single": "{intro}, **{alliance}** memimpin total poin bersih dengan **{score}**.",
        "alliance_net_ranking": "**Peringkat aliansi berdasarkan poin bersih — filter saat ini**",
        "alliance_net_note": "Hanya total poin bersih aliansi yang diperingkat di sini. Peringkat kontribusi positif adalah metrik terpisah dan tidak termasuk dalam daftar ini.",
        "overview_intro": "Istilah poin dapat merujuk pada beberapa metrik. Dengan filter bilah sisi saat ini{period}:",
        "overview_overall": "Pemimpin keseluruhan berdasarkan poin bersih",
        "overview_gained": "Poin yang diperoleh tertinggi",
        "overview_lost": "Poin yang hilang terendah",
        "overview_positive": "Kontribusi positif tertinggi",
        "tie_note": " (seri)",
        "overview_note": "Untuk pertanyaan umum tentang kinerja aliansi, Ask Dashboard menggunakan poin bersih sebagai ukuran default. Sebutkan metrik seperti poin yang diperoleh, poin yang hilang, poin bersih, atau kontribusi positif jika Anda menginginkan satu peringkat tertentu.",
        "alliance_exclusion_intro": "Dengan filter dasbor saat ini{period}, mengecualikan {alliances} mengubah total poin bersih dari **{before}** menjadi **{after}** (**{change}**).",
        "excluded_group": "Kelompok aliansi yang dikecualikan berkontribusi:",
        "players_remaining": "Pemain tersisa: **{after}/{before}**.",
        "exclusion_interpret_negative": "Total membaik karena kelompok aliansi yang dikecualikan memiliki kontribusi bersih negatif dalam cakupan ini.",
        "exclusion_interpret_positive": "Total menurun karena kelompok aliansi yang dikecualikan memiliki kontribusi bersih positif dalam cakupan ini.",
        "exclusion_interpret_zero": "Total tidak berubah karena kelompok aliansi yang dikecualikan memiliki kontribusi bersih nol dalam cakupan ini.",
        "outside_note": "Aliansi berikut sudah berada di luar filter saat ini sehingga tidak memberi efek tambahan: {names}.",
        "net_positive_premise": "Premis tidak sesuai dengan data terfilter saat ini{period}. **{alliance}** berada di peringkat pertama baik untuk total poin bersih ({net}) maupun kontribusi positif ({positive}).",
        "rank_second": "peringkat kedua",
        "rank_not_second": "peringkat #{rank}, bukan kedua",
        "net_positive_main": "Dengan filter bilah sisi saat ini{period}, **{top}** berada di peringkat pertama total poin bersih dengan **{top_net}**, sementara berada di {rank_statement} untuk kontribusi positif dengan **{top_positive}**.",
        "net_positive_detail": "**{leader}** memimpin kontribusi positif dengan **{leader_positive}**, yaitu **{gap}** lebih banyak daripada {top}. Namun, dampak negatif {leader} adalah **{leader_negative}**, dibandingkan **{top_negative}** untuk {top}. Hal ini memberi {top} keunggulan **{advantage}** karena kehilangan poin lebih sedikit.",
        "net_positive_conclusion": "Dampak negatif yang lebih rendah mengimbangi kontribusi positif yang lebih kecil, sehingga {top} unggul atas {leader} sebesar **{lead}** dalam total poin bersih. Di sini, kontribusi positif adalah jumlah poin bersih positif pemain, dan total poin bersih sama dengan kontribusi positif dikurangi dampak negatif.",
        "exclusion_none": "Saat ini tidak ada pemain yang dikecualikan dari kelompok terfilter{period}. Hasil sebelum dan sesudah karena itu sama: **{players} pemain** dengan total poin bersih **{net}**. Hapus setidaknya satu pemain di tab Analisis Pemilihan Pemain untuk membandingkan dampaknya.",
        "exclusion_intro": "Setelah pengecualian saat ini{period}, analisis mencakup **{after} dari {before} pemain**. **Dikecualikan:** {excluded}.",
        "outcome_improved": "Total poin bersih **membaik sebesar {amount}**. Pengecualian menghapus **{negative}** dampak negatif tetapi hanya **{positive}** kontribusi positif, sehingga pengurangan kehilangan poin lebih besar daripada pengurangan kontribusi yang bermanfaat.",
        "outcome_decreased": "Total poin bersih **menurun sebesar {amount}**. Pengecualian menghapus **{positive}** kontribusi positif tetapi hanya **{negative}** dampak negatif, sehingga lebih banyak kontribusi bermanfaat yang dihapus daripada dampak merugikan.",
        "outcome_unchanged": "Total poin bersih tidak berubah. Kontribusi positif yang dihapus (**{positive}**) dan dampak negatif yang dihapus (**{negative}**) saling mengimbangi secara tepat.",
        "negative_no_magnitude": "Persentase negatif tidak dapat dihitung karena kelompok terfilter saat ini tidak memiliki besaran poin bersih positif maupun negatif.",
        "negative_none": "Saat ini tidak ada pemain yang dikecualikan dari kelompok terfilter{period}. Persentase negatif tetap **{share:.1f}%**. Hapus setidaknya satu pemain di tab Analisis Pemilihan Pemain untuk membuat perbandingan sebelum dan sesudah.",
        "negative_after_none": "Setelah pengecualian saat ini{period}, tidak ada besaran poin yang tersisa pada kelompok terpilih, sehingga persentase negatif setelah pengecualian tidak dapat dihitung.",
        "negative_mismatch": "Premis tidak sesuai dengan pilihan saat ini: persentase negatif",
        "negative_normal": "Persentase negatif",
        "negative_increased": "{prefix} **meningkat {change:.1f} poin persentase**, dari **{before:.1f}%** menjadi **{after:.1f}%**.",
        "negative_decreased": "{prefix} **menurun {change:.1f} poin persentase**, dari **{before:.1f}%** menjadi **{after:.1f}%**.",
        "negative_unchanged": "{prefix} pada dasarnya tidak berubah di **{after:.1f}%** ({change:+.1f} poin persentase).",
        "negative_reason_increase_down": "Hal ini terjadi karena pengecualian menghapus proporsi kontribusi positif yang lebih besar daripada dampak negatif. Kontribusi positif turun **{positive_rate:.1f}%**, sementara dampak negatif turun **{negative_rate:.1f}%**. Walaupun dampak negatif mentah juga menurun, porsinya menjadi lebih besar dari total tersisa yang lebih kecil.",
        "negative_reason_increase_same": "Hal ini terjadi karena pengecualian menghapus proporsi kontribusi positif yang lebih besar daripada dampak negatif. Kontribusi positif turun **{positive_rate:.1f}%**, sementara dampak negatif turun **{negative_rate:.1f}%**. Dampak negatif mentah tidak meningkat; nilainya tetap sama tetapi porsinya menjadi lebih besar dari total tersisa yang lebih kecil.",
        "negative_reason_decrease": "Pengecualian menghapus proporsi dampak negatif yang lebih besar daripada kontribusi positif. Dampak negatif turun **{negative_rate:.1f}%**, sementara kontribusi positif turun **{positive_rate:.1f}%**.",
        "negative_reason_unchanged": "Kontribusi positif dan dampak negatif berubah dalam proporsi yang hampir sama, sehingga keseimbangan antara kedua sisi tetap stabil.",
        "negative_intro": "Setelah mengecualikan **{count} pemain**{period} — **{excluded}** — {direction}",
        "removed": "dihapus {amount}, {rate:.1f}%",
        "negative_formula": "Persentase negatif = dampak negatif ÷ (kontribusi positif + dampak negatif).",
        "top_single_intro": "Kontributor teratas{period} diperingkat berdasarkan **poin bersih pemain**.",
        "top_multi_intro": "Karena **{count} aliansi** dipilih{period}, dasbor menampilkan **{top_n}** kontributor teratas dalam setiap aliansi. Pemain diperingkat berdasarkan **poin bersih pemain**.",
        "top_group_positive": "kontributor positif berdasarkan poin bersih",
        "top_group_no_positive": "pemain dengan poin bersih tertinggi; tidak ada pemain dengan poin bersih positif dalam cakupan ini",
        "top_player_detail": "bersih **{net}** (diperoleh {gained}, hilang {lost})",
        "top_player_share": ", **{share:.1f}%** dari kontribusi positif aliansi",
        "top_group_share": "Pemain yang ditampilkan menyumbang **{share:.1f}%** dari kontribusi positif aliansi ini dalam cakupan filter saat ini.",
        "alliance_total": "Total poin bersih aliansi dalam cakupan ini: **{net}**.",
        "excluded_others": "dan {count} lainnya",
        "help_text": "## Cara menggunakan Ask Dashboard\n\n1. Pilih periode SVS dan filter bilah sisi terlebih dahulu.\n2. Tanyakan tentang poin pemain atau aliansi, peringkat, pengecualian, kontribusi positif, atau dampak negatif.\n3. Jawaban hanya menggunakan data yang termasuk dalam filter saat ini.\n\nAsk Dashboard dapat membantu menjelaskan ringkasan skor aliansi, pemain atau aliansi dengan poin bersih tertinggi, kontribusi positif dan dampak negatif, dampak pengecualian pemain, perubahan persentase negatif, kontributor teratas, serta total poin bersih setelah mengecualikan aliansi tertentu.\n\n**Contoh pertanyaan (ketik dalam bahasa Inggris):**\n- Top net score player\n- Top alliance score\n- Which alliance leads net score?\n- Who contributed most in SnS?\n- What changed after excluding the selected players?\n\n**Bantuan lainnya (gunakan perintah bahasa Inggris):** `help filters`, `help questions`, `help player selection`, atau `help limitations`.\n\nAsk Dashboard menjelaskan hasil skor yang tercatat, tetapi tidak dapat menentukan motif, niat, karakter, keterampilan, strategi, tanggung jawab, atau situasi permainan yang tidak tercatat dalam data.",
        "limitation_text": "Ask Dashboard tidak dapat menentukan perilaku, niat, motif, karakter, keterampilan, strategi, tanggung jawab, atau keadaan permainan yang tidak terlihat dari data poin saja.\n\nAsk Dashboard dapat menjelaskan hasil yang tercatat berdasarkan filter saat ini, seperti poin yang diperoleh, poin yang hilang, poin bersih, peringkat, dan total kontribusi. Hasil poin yang sama dapat muncul dari situasi berbeda yang tidak tercatat dalam dataset ini.\n\nSebagai gantinya, Anda dapat menanyakan poin yang diperoleh, poin yang hilang, poin bersih, atau peringkat pemain yang tercatat dalam cakupan saat ini.",
        "rounded_notice": "Catatan data: beberapa nilai poin yang diperoleh untuk periode ini didasarkan pada tampilan Evony di dalam game yang dibulatkan. Oleh karena itu, total, poin bersih, peringkat, dan hasil turunan bersifat perkiraan dan mungkin sedikit berbeda dari nilai tepat."
    }
}


def _format_fields(template):
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }


def validate_answer_copy_parity():
    """Raise early if a locale drifts from the shared answer-copy contract."""
    reference_locale = SUPPORTED_LOCALIZED_ANSWER_LOCALES[0]
    reference = ANSWER_TEXT[reference_locale]
    reference_keys = set(reference)
    for locale in SUPPORTED_LOCALIZED_ANSWER_LOCALES:
        copy = ANSWER_TEXT[locale]
        if set(copy) != reference_keys:
            raise ValueError(f"answer copy keys differ for locale {locale}")
        for key, template in copy.items():
            if not isinstance(template, str) or not template.strip():
                raise ValueError(f"answer copy is blank: {locale}.{key}")
            if _format_fields(template) != _format_fields(reference[key]):
                raise ValueError(f"answer copy placeholders differ: {locale}.{key}")


validate_answer_copy_parity()

_GROUPED_NUMBER_RE = re.compile(r"(?<![\w])([+-]?\d{1,3}(?:,\d{3})+)(?![\w])")
_PERCENT_RE = re.compile(r"(?<![\w])([+-]?\d+(?:\.\d+)?)%")


def _localize_rendered_number_punctuation(rendered, locale):
    """Apply locale punctuation to already-rendered numeric values only."""
    if not isinstance(rendered, str) or locale not in {"fr", "vi"}:
        return rendered

    thousands_separator = "\u202f" if locale == "fr" else "."
    rendered = _GROUPED_NUMBER_RE.sub(
        lambda match: match.group(1).replace(",", thousands_separator),
        rendered,
    )

    def percent(match):
        value = match.group(1).replace(".", ",")
        return value + ("\u202f%" if locale == "fr" else "%")

    return _PERCENT_RE.sub(percent, rendered)


def _t(locale, key, **values):
    return ANSWER_TEXT[locale][key].format(**values)


def _period(locale, period):
    return _t(locale, "period_suffix", period=period) if period else ""


def _scope_intro(answer, locale):
    scope = answer.get("metrics", {}).get(
        "scope", answer.get("parameters", {}).get("scope", "current_filters")
    )
    key = "scope_full" if scope == "server" else "scope_filters"
    return _t(locale, key, period=_period(locale, answer.get("period")))


def _named_scope(answer, locale):
    params = answer.get("parameters", {})
    names = params.get("matched_alliances") or params.get("alliance_names") or []
    joined = "/".join(map(str, names))
    return names, joined, (_t(locale, "scope_named", names=joined) if names else "")


def _excluded_text(players, locale):
    players = list(players or [])
    if len(players) <= 5:
        return ", ".join(map(str, players))
    return ", ".join(map(str, players[:5])) + ", " + _t(
        locale, "excluded_others", count=len(players) - 5
    )


def _unsupported_message(answer, locale):
    question = answer.get("parameters", {}).get("question", "")
    text = legacy.normalize_question_text(question)
    if is_obvious_smalltalk_question(question):
        return _t(locale, "unsupported_smalltalk")
    if re.search(r"\b(?:predict|prediction|future|next svs|will win|winner next)\b", text):
        return _t(locale, "unsupported_prediction")
    return _t(locale, "unsupported_generic")


def _status_message(answer, locale):
    intent = answer.get("intent")
    code = answer.get("guidance_code") or answer.get("error_code")
    params = answer.get("parameters", {})
    metrics = answer.get("metrics", {})
    if code == "missing_columns":
        key = "missing_calculation" if intent == "alliance_exclusion_total_net" else "missing_explanation"
        return _t(locale, key, columns=", ".join(params.get("missing_columns", [])))
    if code == "empty_score_scope":
        return _t(locale, "empty_score_scope")
    if code == "empty_player_scope":
        return _t(locale, "empty_player_scope")
    if code == "requires_multiple_alliances":
        return _t(locale, "requires_multiple_alliances")
    if code == "requires_positive_and_negative_status":
        return _t(
            locale,
            "requires_both_negative" if intent == "negative_share_change" else "requires_both_general",
        )
    if code == "missing_alliance_name":
        available = params.get("available_alliances")
        if available is not None:
            return _t(locale, "missing_alliance_available", available=", ".join(map(str, available)))
        return _t(locale, "missing_alliance_example")
    if code == "alliance_outside_scope":
        names = params.get("outside_scope_alliances") or params.get("alliance_names") or []
        named = ", ".join(f"**{name}**" for name in names)
        if intent in {"top_contributors", "player_net_score_leader"}:
            return _t(locale, "outside_player", names=named)
        return _t(
            locale,
            "outside_exclusion",
            names=named,
            before_net=legacy.format_signed_score(metrics.get("before_net_score", 0)),
        )
    if code == "tied_top_net_score":
        rows = answer.get("rankings", {}).get("alliances", [])
        tied = [row["alliance"] for row in rows if row.get("net_rank") == 1]
        score = next((row.get("total_net_score") for row in rows if row.get("net_rank") == 1), 0)
        return _t(
            locale,
            "tied_net",
            names=", ".join(map(str, tied)),
            score=legacy.format_score(score),
        )
    if code == "no_positive_contribution":
        scope = params.get("scope", metrics.get("scope", "current_filters"))
        return _t(locale, "no_positive_server" if scope == "server" else "no_positive_filters")
    if code == "unsupported_question" or intent == "unsupported_question":
        return _unsupported_message(answer, locale)
    return None


_METRIC_KEYS = (
    (("net score",), "metric_net"),
    (("score gained",), "metric_gained"),
    (("score lost",), "metric_lost"),
    (("positive contribution",), "metric_positive"),
    (("negative impact", "negative contribution"), "metric_negative"),
    (("negative share", "negative percentage", "negative percent", "negative ratio"), "metric_negative_share"),
)


def _metric_definition(answer, locale):
    question = answer.get("parameters", {}).get("question", "")
    text = legacy.normalize_question_text(question)
    for aliases, key in _METRIC_KEYS:
        if any(alias in text for alias in aliases):
            return _t(locale, key)
    return None


def _render_alliance_positive(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    metrics = answer["metrics"]
    leaders = metrics.get("leaders", [])
    intro = _scope_intro(answer, locale)
    if metrics.get("leader_count", 0) > 1:
        names = ", ".join(f"**{row['alliance']}**" for row in leaders)
        return _t(
            locale,
            "alliance_positive_tie",
            intro=intro,
            names=names,
            score=legacy.format_signed_score(metrics["top_positive_contribution"]),
        )
    leader = leaders[0]
    rows = answer.get("rankings", {}).get("alliances", [])
    ranking = "\n".join(
        f"{row['rank']}. **{row['alliance']}** — {legacy.format_score(row['positive_contribution'])} ({row['share_of_scope_positive']:.1f}%)"
        for row in rows[:5]
    )
    return (
        _t(
            locale,
            "alliance_positive_single",
            intro=intro,
            alliance=leader["alliance"],
            score=legacy.format_signed_score(leader["positive_contribution"]),
        )
        + "\n\n"
        + _t(locale, "positive_share", share=leader["share_of_scope_positive"])
        + "\n\n"
        + _t(locale, "positive_ranking")
        + "\n"
        + ranking
    )


def _render_player_positive(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    metrics = answer["metrics"]
    leaders = metrics.get("leaders", [])
    intro = _scope_intro(answer, locale)
    names, _, scope = _named_scope(answer, locale)
    if metrics.get("leader_count", 0) > 1:
        tied = ", ".join(
            f"**{row['player_name']}** ({row['alliance']})" for row in leaders
        )
        return _t(
            locale,
            "player_positive_tie",
            intro=intro,
            scope=scope,
            names=tied,
            score=legacy.format_signed_score(metrics["top_positive_contribution"]),
        )
    top = leaders[0]
    return (
        _t(
            locale,
            "player_positive_single",
            intro=intro,
            scope=scope,
            player=top["player_name"],
            score=legacy.format_signed_score(top["positive_contribution"]),
        )
        + "\n\n"
        + f"- **{_t(locale, 'label_alliance')}:** {top['alliance']}\n"
        + f"- **{_t(locale, 'label_score_gained')}:** {legacy.format_score(top['score_gained'])}\n"
        + f"- **{_t(locale, 'label_score_lost')}:** {legacy.format_score(top['score_lost'])}\n"
        + f"- **{_t(locale, 'label_share_positive')}:** {top['share_of_scope_positive']:.1f}%"
    )


def _render_player_net(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    metrics = answer.get("metrics", {})
    rows = answer.get("rankings", {}).get("players", [])
    _, joined, scope = _named_scope(answer, locale)
    intro = _t(locale, "scope_filters", period=_period(locale, answer.get("period")))
    leaders = metrics.get("leaders") or [row for row in rows if row.get("rank") == 1]
    if metrics.get("leader_count", len(leaders)) > 1:
        names = ", ".join(
            f"**{row['player_name']}**" + (f" ({row['alliance']})" if not joined else "")
            for row in leaders
        )
        first = _t(
            locale,
            "player_net_tie",
            intro=intro,
            scope=scope,
            names=names,
            score=legacy.format_signed_score(metrics["top_net_score"]),
        )
    else:
        top = next((row for row in rows if row.get("rank") == 1), rows[0])
        first = _t(
            locale,
            "player_net_single",
            intro=intro,
            scope=scope,
            player=top["player_name"],
            score=legacy.format_signed_score(top["net_score"]),
        )
    title = _t(locale, "player_ranking_named", names=joined) if joined else _t(locale, "player_ranking_filters")
    ranking_lines = []
    for row in rows[:3]:
        alliance = "" if joined else f" ({row['alliance']})"
        ranking_lines.append(
            f"{row['rank']}. **{row['player_name']}**{alliance} — **{legacy.format_signed_score(row['net_score'])}**"
        )
    boundary = _t(locale, "player_boundary_named", names=joined) if joined else _t(locale, "player_boundary_filters")
    return f"{first}\n\n{title}\n" + "\n".join(ranking_lines) + f"\n\n{boundary}"


def _render_alliance_net(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    metrics = answer.get("metrics", {})
    rows = answer.get("rankings", {}).get("alliances", [])
    intro = _t(locale, "scope_filters", period=_period(locale, answer.get("period")))
    leaders = metrics.get("leaders", [])
    if metrics.get("leader_count", len(leaders)) > 1:
        names = ", ".join(f"**{row['alliance']}**" for row in leaders)
        first = _t(
            locale,
            "alliance_net_tie",
            intro=intro,
            names=names,
            score=legacy.format_signed_score(metrics["top_net_score"]),
        )
    else:
        leader = leaders[0]
        first = _t(
            locale,
            "alliance_net_single",
            intro=intro,
            alliance=leader["alliance"],
            score=legacy.format_signed_score(leader["total_net_score"]),
        )
    ranking = "\n".join(
        f"{row['net_rank']}. **{row['alliance']}** — **{legacy.format_signed_score(row['total_net_score'])}**"
        for row in rows
    )
    return f"{first}\n\n{_t(locale, 'alliance_net_ranking')}\n{ranking}\n\n{_t(locale, 'alliance_net_note')}"


def _render_overview(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    metrics = answer["metrics"]

    def metric_line(label_key, rows, field, *, signed=False):
        names = ", ".join(f"**{row['alliance']}**" for row in rows)
        value = rows[0][field]
        formatted = legacy.format_signed_score(value) if signed else legacy.format_score(value)
        tie = _t(locale, "tie_note") if len(rows) > 1 else ""
        return f"- **{_t(locale, label_key)}:** {names} — **{formatted}**{tie}"

    return (
        _t(locale, "overview_intro", period=_period(locale, answer.get("period")))
        + "\n\n"
        + metric_line("overview_overall", metrics["net_score_leaders"], "total_net_score", signed=True)
        + "\n"
        + metric_line("overview_gained", metrics["score_gained_leaders"], "total_score_gained")
        + "\n"
        + metric_line("overview_lost", metrics["lowest_score_lost_leaders"], "total_score_lost")
        + "\n"
        + metric_line("overview_positive", metrics["positive_contribution_leaders"], "positive_contribution")
        + "\n\n"
        + _t(locale, "overview_note")
    )


def _render_alliance_exclusion(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    params = answer["parameters"]
    metrics = answer["metrics"]
    alliances = params.get("recognized_alliances", params.get("excluded_alliances", []))
    alliance_text = ", ".join(f"**{name}**" for name in alliances)
    excluded_net = metrics["excluded_net_score"]
    interpretation_key = (
        "exclusion_interpret_negative" if excluded_net < 0 else
        "exclusion_interpret_positive" if excluded_net > 0 else
        "exclusion_interpret_zero"
    )
    outside = params.get("outside_scope_alliances", [])
    outside_note = ""
    if outside:
        outside_note = "\n\n" + _t(
            locale,
            "outside_note",
            names=", ".join(f"**{name}**" for name in outside),
        )
    return (
        _t(
            locale,
            "alliance_exclusion_intro",
            period=_period(locale, answer.get("period")),
            alliances=alliance_text,
            before=legacy.format_signed_score(metrics["before_net_score"]),
            after=legacy.format_signed_score(metrics["after_net_score"]),
            change=legacy.format_signed_score(metrics["net_score_change"]),
        )
        + "\n\n"
        + _t(locale, "excluded_group")
        + "\n"
        + f"- {_t(locale, 'label_score_gained')}: **{legacy.format_score(metrics['excluded_score_gained'])}**\n"
        + f"- {_t(locale, 'label_score_lost')}: **{legacy.format_score(metrics['excluded_score_lost'])}**\n"
        + f"- {_t(locale, 'label_net_score')}: **{legacy.format_signed_score(metrics['excluded_net_score'])}**\n\n"
        + _t(locale, "players_remaining", after=metrics["after_player_count"], before=metrics["before_player_count"])
        + " "
        + _t(locale, interpretation_key)
        + outside_note
    )


def _render_net_vs_positive(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    rows = answer.get("rankings", {}).get("alliances", [])
    metrics = answer["metrics"]
    top = next(row for row in rows if row.get("alliance") == metrics.get("top_net_alliance"))
    period = _period(locale, answer.get("period"))
    if top.get("positive_rank") == 1:
        return _t(
            locale,
            "net_positive_premise",
            period=period,
            alliance=top["alliance"],
            net=legacy.format_score(top["total_net_score"]),
            positive=legacy.format_score(top["positive_net_score"]),
        )
    leader = next(row for row in rows if row.get("alliance") == metrics.get("positive_leader_alliance"))
    rank_statement = _t(locale, "rank_second") if top.get("positive_rank") == 2 else _t(
        locale, "rank_not_second", rank=top.get("positive_rank")
    )
    return (
        _t(
            locale,
            "net_positive_main",
            period=period,
            top=top["alliance"],
            top_net=legacy.format_score(top["total_net_score"]),
            rank_statement=rank_statement,
            top_positive=legacy.format_score(top["positive_net_score"]),
        )
        + "\n\n"
        + _t(
            locale,
            "net_positive_detail",
            leader=leader["alliance"],
            leader_positive=legacy.format_score(leader["positive_net_score"]),
            gap=legacy.format_score(metrics["positive_gap"]),
            top=top["alliance"],
            leader_negative=legacy.format_score(leader["negative_impact"]),
            top_negative=legacy.format_score(top["negative_impact"]),
            advantage=legacy.format_score(metrics["negative_advantage"]),
        )
        + "\n\n"
        + _t(
            locale,
            "net_positive_conclusion",
            top=top["alliance"],
            leader=leader["alliance"],
            lead=legacy.format_score(metrics["net_lead"]),
        )
    )


def _render_exclusion(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    m = answer["metrics"]
    before = m["before"]
    after = m["after"]
    changes = m["changes"]
    period = _period(locale, answer.get("period"))
    if m["excluded_player_count"] == 0:
        return _t(
            locale,
            "exclusion_none",
            period=period,
            players=m["before_player_count"],
            net=legacy.format_score(before["net_score"]),
        )
    net_change = changes["net_score"]
    if net_change > 0:
        outcome = _t(
            locale,
            "outcome_improved",
            amount=legacy.format_score(net_change),
            negative=legacy.format_score(m["negative_removed"]),
            positive=legacy.format_score(m["positive_removed"]),
        )
    elif net_change < 0:
        outcome = _t(
            locale,
            "outcome_decreased",
            amount=legacy.format_score(abs(net_change)),
            negative=legacy.format_score(m["negative_removed"]),
            positive=legacy.format_score(m["positive_removed"]),
        )
    else:
        outcome = _t(
            locale,
            "outcome_unchanged",
            negative=legacy.format_score(m["negative_removed"]),
            positive=legacy.format_score(m["positive_removed"]),
        )
    excluded = _excluded_text(answer.get("parameters", {}).get("excluded_players", []), locale)
    return (
        _t(
            locale,
            "exclusion_intro",
            period=period,
            after=m["after_player_count"],
            before=m["before_player_count"],
            excluded=excluded,
        )
        + "\n\n"
        + f"- **{_t(locale, 'label_score_gained')}:** {legacy.format_score(before['score_gained'])} → {legacy.format_score(after['score_gained'])} ({legacy.format_signed_score(changes['score_gained'])})\n"
        + f"- **{_t(locale, 'label_score_lost')}:** {legacy.format_score(before['score_lost'])} → {legacy.format_score(after['score_lost'])} ({legacy.format_signed_score(changes['score_lost'])})\n"
        + f"- **{_t(locale, 'label_positive_contribution')}:** {legacy.format_score(before['positive_contribution'])} → {legacy.format_score(after['positive_contribution'])} ({legacy.format_signed_score(changes['positive_contribution'])})\n"
        + f"- **{_t(locale, 'label_negative_impact')}:** {legacy.format_score(before['negative_impact'])} → {legacy.format_score(after['negative_impact'])} ({legacy.format_signed_score(changes['negative_impact'])})\n"
        + f"- **{_t(locale, 'label_total_net')}:** {legacy.format_score(before['net_score'])} → {legacy.format_score(after['net_score'])} ({legacy.format_signed_score(changes['net_score'])})\n\n"
        + outcome
    )


def _render_negative_share(answer, locale):
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    m = answer["metrics"]
    before = m["before"]
    after = m["after"]
    period = _period(locale, answer.get("period"))
    if before.get("negative_share") is None:
        return _t(locale, "negative_no_magnitude")
    if m["excluded_player_count"] == 0:
        return _t(locale, "negative_none", period=period, share=before["negative_share"])
    if after.get("negative_share") is None:
        return _t(locale, "negative_after_none", period=period)
    share_change = m["share_change"]
    actual_direction = "increase" if share_change > 0.05 else "decrease" if share_change < -0.05 else "unchanged"
    requested = answer.get("parameters", {}).get("requested_direction", "unspecified")
    mismatch = requested in {"increase", "decrease"} and actual_direction != requested
    prefix = _t(locale, "negative_mismatch" if mismatch else "negative_normal")
    positive_removed = m["positive_removed"]
    negative_removed = m["negative_removed"]
    positive_rate = positive_removed / before["positive"] * 100 if before["positive"] > 0 else 0
    negative_rate = negative_removed / before["negative"] * 100 if before["negative"] > 0 else 0
    if share_change > 0.05:
        direction = _t(
            locale,
            "negative_increased",
            prefix=prefix,
            change=share_change,
            before=before["negative_share"],
            after=after["negative_share"],
        )
        reason = _t(
            locale,
            "negative_reason_increase_down" if negative_removed > 0 else "negative_reason_increase_same",
            positive_rate=positive_rate,
            negative_rate=negative_rate,
        )
    elif share_change < -0.05:
        direction = _t(
            locale,
            "negative_decreased",
            prefix=prefix,
            change=abs(share_change),
            before=before["negative_share"],
            after=after["negative_share"],
        )
        reason = _t(
            locale,
            "negative_reason_decrease",
            positive_rate=positive_rate,
            negative_rate=negative_rate,
        )
    else:
        direction = _t(
            locale,
            "negative_unchanged",
            prefix=prefix,
            after=after["negative_share"],
            change=share_change,
        )
        reason = _t(locale, "negative_reason_unchanged")
    excluded = _excluded_text(answer.get("parameters", {}).get("excluded_players", []), locale)
    return (
        _t(
            locale,
            "negative_intro",
            count=m["excluded_player_count"],
            period=period,
            excluded=excluded,
            direction=direction,
        )
        + "\n\n"
        + f"- **{_t(locale, 'label_positive_contribution')}:** {legacy.format_score(before['positive'])} → {legacy.format_score(after['positive'])} ({_t(locale, 'removed', amount=legacy.format_score(positive_removed), rate=positive_rate)})\n"
        + f"- **{_t(locale, 'label_negative_impact')}:** {legacy.format_score(before['negative'])} → {legacy.format_score(after['negative'])} ({_t(locale, 'removed', amount=legacy.format_score(negative_removed), rate=negative_rate)})\n\n"
        + reason
        + "\n\n"
        + _t(locale, "negative_formula")
    )


def _render_top_contributors(answer, locale):
    if answer.get("metrics", {}).get("mode") == "leader":
        return _render_player_positive(answer, locale)
    guidance = _status_message(answer, locale)
    if guidance:
        return guidance
    groups = answer.get("rankings", {}).get("alliances", [])
    period = _period(locale, answer.get("period"))
    single = len(groups) == 1
    top_n = answer.get("metrics", {}).get("top_n", 5 if single else 3)
    intro = (
        _t(locale, "top_single_intro", period=period)
        if single
        else _t(locale, "top_multi_intro", count=len(groups), period=period, top_n=top_n)
    )
    sections = []
    for group in groups:
        description = _t(
            locale,
            "top_group_positive" if group.get("positive_total", 0) > 0 else "top_group_no_positive",
        )
        lines = [f"**{group['alliance']}** — {description}:"]
        for rank, row in enumerate(group.get("players", []), start=1):
            details = _t(
                locale,
                "top_player_detail",
                net=legacy.format_signed_score(row["net_score"]),
                gained=legacy.format_score(row["score_gained"]),
                lost=legacy.format_score(row["score_lost"]),
            )
            if row.get("share_of_positive") is not None:
                details += _t(locale, "top_player_share", share=row["share_of_positive"])
            lines.append(f"{rank}. **{row['player_name']}** — {details}")
        if group.get("positive_total", 0) > 0:
            ranked_total = sum(
                row["net_score"] for row in group.get("players", []) if row["net_score"] > 0
            )
            lines.append(
                _t(
                    locale,
                    "top_group_share",
                    share=ranked_total / group["positive_total"] * 100,
                )
            )
        lines.append(_t(locale, "alliance_total", net=legacy.format_signed_score(group["net_total"])))
        sections.append("\n".join(lines))
    return intro + "\n\n" + "\n\n".join(sections)


def _show_notice(answer):
    period = legacy._parse_svs_period(answer.get("period"))
    if period is None or answer.get("status") != "ok":
        return False
    if answer.get("intent") not in SCORE_DERIVED_INTENTS:
        return False
    return period >= legacy.ROUNDED_SCORE_GAINED_START_PERIOD and (
        legacy.ROUNDED_SCORE_GAINED_END_PERIOD is None
        or period <= legacy.ROUNDED_SCORE_GAINED_END_PERIOD
    )


def render_localized_dashboard_answer(answer, locale):
    """Return localized Markdown, or None when the English renderer should be used."""
    if locale not in SUPPORTED_LOCALIZED_ANSWER_LOCALES:
        return None
    if not isinstance(answer, dict):
        return str(answer)

    intent = answer.get("intent")
    if intent == "dashboard_help":
        rendered = _metric_definition(answer, locale) or _t(locale, "help_text")
    elif intent == "dashboard_limitation":
        rendered = _t(locale, "limitation_text")
    elif intent == "unsupported_question":
        rendered = _status_message(answer, locale) or _unsupported_message(answer, locale)
    elif intent == ALLIANCE_POSITIVE_CONTRIBUTION_INTENT:
        rendered = _render_alliance_positive(answer, locale)
    elif intent == "player_net_score_leader":
        rendered = _render_player_net(answer, locale)
    elif intent == "top_contributors":
        rendered = _render_top_contributors(answer, locale)
    elif intent == "net_score_leader_summary":
        rendered = _render_alliance_net(answer, locale)
    elif intent == "alliance_score_overview":
        rendered = _render_overview(answer, locale)
    elif intent == "alliance_exclusion_total_net":
        rendered = _render_alliance_exclusion(answer, locale)
    elif intent == "net_vs_positive_ranking":
        rendered = _render_net_vs_positive(answer, locale)
    elif intent == "player_exclusion_impact":
        rendered = _render_exclusion(answer, locale)
    elif intent == "negative_share_change":
        rendered = _render_negative_share(answer, locale)
    else:
        rendered = _status_message(answer, locale)
        if rendered is None:
            return None

    if _show_notice(answer):
        rendered += "\n\n---\n\n" + _t(locale, "rounded_notice")
    return _localize_rendered_number_punctuation(rendered, locale)
