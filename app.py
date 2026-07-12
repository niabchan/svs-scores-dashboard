import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import re

# Clean player names for display while preserving letters from all languages.
def clean_player_name(name):
    if pd.isna(name):
        return name

    original_name = str(name).strip()

    # NFC keeps accented letters such as ó, é, â, and ầ intact.
    normalized_name = unicodedata.normalize("NFC", original_name)

    cleaned = []

    for char in normalized_name:
        category = unicodedata.category(char)

        if (
            category.startswith("L")      # Letters from all languages
            or category.startswith("M")   # Combining accents and marks
            or category.startswith("N")   # Numbers
            or category.startswith("S")
            or char.isspace()
            or char in "_-'’."
        ):
            cleaned.append(char)

    # Remove leading/trailing spaces and collapse repeated spaces.
    result = " ".join("".join(cleaned).split())

    # Keep the original name if cleaning removes everything.
    return result or original_name

# Language
LANGUAGES = {
    "English": "en",
    "Español": "es",
    "Français": "fr",
    "Tiếng Việt": "vi",
    "Bahasa Indonesia": "id"
}

TEXT = {
    "en": {
        "app_title": "SVS Scores Dashboard",
        "app_caption": "Explore player and alliance impact on SVS results for Server 559+461.",
        "filters": "Filters",
        "language": "Language",
        "svs_period": "SVS Period",
        "select_alliances": "Select alliances",
        "select_net_status": "Select net status",
        "sidebar_caption": "Filters affect all charts and tables. Overview metrics show the full server total for the selected SVS period.",
        "overview": "Overview",
        "alliance_summary": "Alliance Summary",
        "alliance_summary_caption": "Compare score gained, score lost, net score, and player counts across alliances.",
        "player_data": "Player Data",
        "player_data_caption": "Filtered player-level SVS data used in the charts and analysis.",
        "player_rankings": "Player Rankings",
        "select_ranking_view": "Select a ranking view",
        "top_10_net_score": "Top 10 Net Score",
        "bottom_10_net_score": "Bottom 10 Net Score",
        "top_10_score_gained": "Top 10 Score Gained",
        "top_10_score_lost": "Top 10 Score Lost",
        "contribution_insight": "Contribution Insight",
        "contribution_insight_caption": "View how selected alliances contribute to positive and negative SVS results.",
        "contribution_share": "### Contribution Share",
        "contribution_share_caption": "Positive share shows which alliances generated positive net scores. Negative share shows which alliances generated negative net scores.",
        "positive_contribution": "**Positive Contribution**",
        "negative_contribution": "**Negative Contribution**",
        "positive_side": "**Positive Side**",
        "negative_side": "**Negative Side**",
        "contribution_details": "### Contribution Details",
        "contribution_details_caption": "Tables provide the exact values behind the pie charts.",
        "no_positive_net_score": "No positive net score found in the selected data.",
        "no_negative_net_score": "No negative net score found in the selected data.",
        "negative_chart_explanation": "The negative chart uses absolute values to show each alliance's share of the total negative impact.",
        "player_selection_insight": "Player Selection Insight",
        "player_selection_insight_caption": "Use this tab to see how adding or removing players changes the filtered server-level results and alliance-level summary.",
        "score": "Score",
        "score_gained": "Score Gained",
        "score_lost": "Score Lost",
        "net_score": "Net Score",
        "svs_rank": "SVS Rank",
        "players": "Players",
        "alliance": "Alliance",
        "player": "Player",
        "filtered_players": "Filtered Players",
        "selected_players": "Selected Players",
        "excluded_players": "Excluded Players",
        "no_excluded_players": "No players are excluded. All filtered players are currently included.",
        "positive": "Positive",
        "negative": "Negative",
        "positive_players": "Positive Players",
        "negative_players": "Negative Players",
        "total_net_score": "Total Net Score",
        "net_per_player": "Net per Player",
        "ranking_chart_guide":
        """
        **How to use:**
        By default, the ranking chart compares players from the alliances currently selected in the sidebar. To view a server-wide player ranking, open the alliance filter and choose **Select all**.
        """,
        "status": "Status",
        "score_gained_vs_net_score": "Score Gained vs Net Score",
        "scatter_chart_caption": "Each dot represents one player. Points above zero indicate a positive net score, while points below zero indicate a negative net score.",
        "total_net_score_by_alliance": "Total Net Score by Alliance",
        "total_net_score_by_alliance_caption": "Compare total net score across alliances based on the current filters.",
        "net_score_per_player_by_alliance": "Net Score per Player by Alliance",
        "net_score_per_player_by_alliance_caption": "Compare average net score per player across alliances. This helps balance comparisons between large and small alliances.",
        "positive_net": "Positive Net",
        "negative_net": "Negative Net",
        "zero_net_score": "Zero net score",
        "share": "Share",
        "share_percent": "Share (%)",
        "contribution_reading_guide":
        """
        **How to read this section:**
        Positive Contribution Share shows which alliances generated the server’s positive net scores.
        Negative Contribution Share shows which alliances generated the server’s negative net scores.
        These results reflect the current sidebar filters.
        """,
        "choose_players_to_include": "1. Choose Players to Include",
        "choose_players_caption": "Selected players are included in the analysis. Remove players to see how the results change without them.",
        "select_players_to_include": "Choose players to include",
        "excluded_players_caption": "These players are currently excluded from the selected-group analysis.",
        "selected_group_impact": "2. Selected Group Impact",
        "selected_group_impact_caption": "This section shows the combined results of the selected players within the current sidebar filters.",
        "positive_negative_net_contribution": "3. Positive and Negative Net Contribution",
        "score_balance_caption": "The left chart shows all players within the current sidebar filters. The right chart shows only the selected players after exclusions.",
        "before_exclusion": "**Before Exclusion**",
        "before_exclusion_caption": "All players within the current sidebar filters.",
        "after_exclusion": "**After Exclusion**",
        "after_exclusion_caption": "Only selected players. Excluded players are not included in this chart.",
        "alliance_impact_selected_players": "4. Alliance Impact of Selected Players",
        "alliance_impact_selected_players_caption": "This section shows how the selected players contribute to each alliance. It shows the full results for an alliance only when all of its players are selected.",
        "no_players_selected_alliance_summary": "No players are selected. Select at least one player to show the alliance summary."
    },
    "es": {
        "app_title": "Panel de puntuaciones SVS",
        "app_caption": "Explora el impacto de los jugadores y las alianzas en los resultados de SVS del Servidor 559+461.",
        "filters": "Filtros",
        "language": "Idioma",
        "svs_period": "Período de SVS",
        "select_alliances": "Seleccionar alianzas",
        "select_net_status": "Seleccionar estado neto",
        "sidebar_caption": "Los filtros afectan todos los gráficos y tablas. Las métricas de Resumen muestran el total completo del servidor para el período de SVS seleccionado.",
        "overview": "Resumen general",
        "alliance_summary": "Resumen de alianzas",
        "alliance_summary_caption": "Compare los puntos obtenidos, los puntos perdidos, la puntuación neta y el número de jugadores entre las alianzas.",
        "player_data": "Datos de jugadores",
        "player_data_caption": "Datos SVS filtrados a nivel de jugador utilizados en los gráficos y análisis.",
        "player_rankings": "Clasificación de jugadores",
        "select_ranking_view": "Seleccione una vista de clasificación",
        "top_10_net_score": "Top 10 puntuación neta",
        "bottom_10_net_score": "Últimos 10 en puntuación neta",
        "top_10_score_gained": "Top 10 puntos obtenidos",
        "top_10_score_lost": "Top 10 puntos perdidos",
        "contribution_insight": "Análisis de contribución",
        "contribution_insight_caption": "Vea cómo las alianzas seleccionadas contribuyen a los resultados positivos y negativos del SVS.",
        "contribution_share": "### Tasa de contribución",
        "contribution_share_caption": "La participación positiva muestra qué alianzas generaron puntuaciones netas positivas. La participación negativa muestra qué alianzas generaron puntuaciones netas negativas.",
        "positive_contribution": "**Contribución positiva**",
        "negative_contribution": "**Contribución negativa**",
        "positive_side": "**Lado positivo**",
        "negative_side": "**Lado negativo**",
        "contribution_details": "### Detalles de contribución",
        "contribution_details_caption": "Las tablas muestran los valores exactos representados en los gráficos circulares.",
        "no_positive_net_score": "No se encontró ninguna puntuación neta positiva en los datos seleccionados.",
        "no_negative_net_score": "No se encontró ninguna puntuación neta negativa en los datos seleccionados.",
        "negative_chart_explanation": "El gráfico negativo utiliza valores absolutos para mostrar la participación de cada alianza en el impacto negativo total.",
        "player_selection_insight": "Análisis de selección de jugadores",
        "player_selection_insight_caption": "Utilice esta pestaña para ver cómo añadir o eliminar jugadores cambia los resultados filtrados a nivel del servidor y el resumen por alianza.",
        "score": "Puntuación",
        "score_gained": "Puntos obtenidos",
        "score_lost": "Puntos perdidos",
        "net_score": "Puntuación neta",
        "svs_rank": "Rango SVS",
        "players": "Jugadores",
        "alliance": "Alianza",
        "player": "Jugador",
        "filtered_players": "Jugadores filtrados",
        "selected_players": "Jugadores seleccionados",
        "excluded_players": "Jugadores excluidos",
        "no_excluded_players": "No hay jugadores excluidos. Todos los jugadores filtrados están incluidos actualmente.",
        "positive": "Positivo",
        "negative": "Negativo",
        "positive_players": "Jugadores positivos",
        "negative_players": "Jugadores negativos",
        "total_net_score": "Puntuación neta total",
        "net_per_player": "Puntuación neta por jugador",
        "ranking_chart_guide":
        """
        **Cómo utilizarlo:**
        De forma predeterminada, el gráfico de clasificación compara a los jugadores de las alianzas seleccionadas actualmente en la barra lateral. Para ver una clasificación de jugadores de todo el servidor, abra el filtro de alianzas y elija **Select all**.
        """,
        "status": "Estado",
        "score_gained_vs_net_score": "Puntos obtenidos vs Puntuación neta",
        "scatter_chart_caption": "Cada punto representa a un jugador. Los puntos por encima de cero indican una puntuación neta positiva, mientras que los puntos por debajo de cero indican una puntuación neta negativa.",
        "total_net_score_by_alliance": "Puntuación neta total por alianza",
        "total_net_score_by_alliance_caption": "Compare la puntuación neta total entre las alianzas según los filtros actuales.",
        "net_score_per_player_by_alliance": "Puntuación neta por jugador por alianza",
        "net_score_per_player_by_alliance_caption": "Compare la puntuación neta media por jugador entre las alianzas. Esto ayuda a equilibrar las comparaciones entre alianzas grandes y pequeñas.",
        "positive_net": "Neto positivo",
        "negative_net": "Neto negativo",
        "zero_net_score": "Puntuación neta cero",
        "share": "Participación",
        "share_percent": "Participación (%)",
        "contribution_reading_guide":
        """
        **Cómo interpretar esta sección:**
        La participación en la contribución positiva muestra qué alianzas generaron las puntuaciones netas positivas del servidor.
        La participación en la contribución negativa muestra qué alianzas generaron las puntuaciones netas negativas del servidor.
        Estos resultados reflejan los filtros actuales de la barra lateral.
        """,
        "choose_players_to_include": "1. Seleccione los jugadores que desea incluir",
        "choose_players_caption": "Los jugadores seleccionados se incluyen en el análisis. Elimine jugadores para ver cómo cambian los resultados sin ellos.",
        "select_players_to_include": "Seleccione los jugadores que desea incluir",
        "excluded_players_caption": "Estos jugadores están actualmente excluidos del análisis del grupo seleccionado.",
        "selected_group_impact": "2. Impacto del grupo seleccionado",
        "selected_group_impact_caption": "Esta sección muestra los resultados combinados de los jugadores seleccionados según los filtros actuales de la barra lateral.",
        "positive_negative_net_contribution": "3. Contribuciones netas positivas y negativas",
        "score_balance_caption": "El gráfico de la izquierda muestra a todos los jugadores incluidos en los filtros actuales de la barra lateral. El gráfico de la derecha muestra únicamente a los jugadores seleccionados después de las exclusiones.",
        "before_exclusion": "**Antes de las exclusiones**",
        "before_exclusion_caption": "Todos los jugadores incluidos en los filtros actuales de la barra lateral.",
        "after_exclusion": "**Después de las exclusiones**",
        "after_exclusion_caption": "Solo se muestran los jugadores seleccionados. Los jugadores excluidos no se incluyen en este gráfico.",
        "alliance_impact_selected_players": "4. Impacto de los jugadores seleccionados en las alianzas",
        "alliance_impact_selected_players_caption": "Esta sección muestra cómo contribuyen los jugadores seleccionados a cada alianza. Solo muestra los resultados completos de una alianza cuando están seleccionados todos sus jugadores.",
        "no_players_selected_alliance_summary": "No hay jugadores seleccionados. Seleccione al menos un jugador para mostrar el resumen por alianza."
    },
    "fr": {
        "app_title": "Tableau de bord des scores SVS",
        "app_caption": "Explorez l’impact des joueurs et des alliances sur les résultats du SVS du serveur 559+461.",
        "filters": "Filtres",
        "language": "Langue",
        "svs_period": "Période SVS",
        "select_alliances": "Sélectionner les alliances",
        "select_net_status": "Sélectionner le statut net",
        "sidebar_caption": "Les filtres affectent tous les graphiques et tableaux. Les indicateurs de la vue d’ensemble affichent le total complet du serveur pour la période SVS sélectionnée.",
        "overview": "Vue d'ensemble",
        "alliance_summary": "Résumé des alliances",
        "alliance_summary_caption": "Comparez le score gagné, le score perdu, le score net et le nombre de joueurs entre les alliances.",
        "player_data": "Données des joueurs",
        "player_data_caption": "Données SVS filtrées au niveau des joueurs utilisées dans les graphiques et les analyses.",
        "player_rankings": "Classement des joueurs",
        "select_ranking_view": "Sélectionnez une vue du classement",
        "top_10_net_score": "Top 10 score net",
        "bottom_10_net_score": "Bottom 10 score net",
        "top_10_score_gained": "Top 10 points gagnés",
        "top_10_score_lost": "Top 10 points perdus",
        "contribution_insight": "Analyse des contributions",
        "contribution_insight_caption": "Découvrez comment les alliances sélectionnées contribuent aux résultats positifs et négatifs du SVS.",
        "contribution_share": "### Part de contribution",
        "contribution_share_caption": "La part positive montre quelles alliances ont généré des scores nets positifs. La part négative montre quelles alliances ont généré des scores nets négatifs.",
        "positive_contribution": "**Contribution positive**",
        "negative_contribution": "**Contribution négative**",
        "positive_side": "**Côté positif**",
        "negative_side": "**Côté négatif**",
        "contribution_details": "### Détails des contributions",
        "contribution_details_caption": "Les tableaux présentent les valeurs exactes représentées dans les diagrammes circulaires.",
        "no_positive_net_score": "Aucun score net positif n'a été trouvé dans les données sélectionnées.",
        "no_negative_net_score": "Aucun score net négatif n'a été trouvé dans les données sélectionnées.",
        "negative_chart_explanation": "Le graphique négatif utilise des valeurs absolues pour montrer la part de chaque alliance dans l'impact négatif total.",
        "player_selection_insight": "Analyse de la sélection des joueurs",
        "player_selection_insight_caption": "Utilisez cet onglet pour voir comment l’ajout ou la suppression de joueurs modifie les résultats filtrés au niveau du serveur et le résumé par alliance.",
        "score": "Score",
        "score_gained": "Points gagnés",
        "score_lost": "Points perdus",
        "net_score": "Score net",
        "svs_rank": "Rang SVS",
        "players": "Joueurs",
        "alliance": "Alliance",
        "player": "Joueur",
        "filtered_players": "Joueurs filtrés",
        "selected_players": "Joueurs sélectionnés",
        "excluded_players": "Joueurs exclus",
        "no_excluded_players": "Aucun joueur n’est exclu. Tous les joueurs filtrés sont actuellement inclus.",
        "positive": "Positif",
        "negative": "Négatif",
        "positive_players": "Joueurs positifs",
        "negative_players": "Joueurs négatifs",
        "total_net_score": "Score net total",
        "net_per_player": "Score net par joueur",
        "ranking_chart_guide":
        """
        **Comment l’utiliser :** Par défaut, le graphique de classement compare les joueurs des alliances actuellement sélectionnées dans la barre latérale. Pour afficher un classement des joueurs à l’échelle du serveur, ouvrez le filtre des alliances et choisissez **Select all**.
        """,
        "status": "Statut",
        "score_gained_vs_net_score": "Points gagnés vs Score net",
        "scatter_chart_caption": "Chaque point représente un joueur. Les points au-dessus de zéro indiquent un score net positif, tandis que les points en dessous de zéro indiquent un score net négatif.",
        "total_net_score_by_alliance": "Score net total par alliance",
        "total_net_score_by_alliance_caption": "Comparez le score net total entre les alliances selon les filtres actuels.",
        "net_score_per_player_by_alliance": "Score net par joueur par alliance",
        "net_score_per_player_by_alliance_caption": "Comparez le score net moyen par joueur entre les alliances. Cela permet d'équilibrer les comparaisons entre les grandes et les petites alliances.",
        "positive_net": "Score net positif",
        "negative_net": "Score net négatif",
        "zero_net_score": "Score net nul",
        "share": "Part",
        "share_percent": "Part (%)",
        "contribution_reading_guide":
        """
        **Comment interpréter cette section :**
        La part de contribution positive indique quelles alliances ont généré les scores nets positifs du serveur.
        La part de contribution négative indique quelles alliances ont généré les scores nets négatifs du serveur.
        Ces résultats reflètent les filtres actuels de la barre latérale.
        """,
        "choose_players_to_include": "1. Sélectionnez les joueurs à inclure",
        "choose_players_caption": "Les joueurs sélectionnés sont inclus dans l’analyse. Retirez des joueurs pour voir comment les résultats changent sans eux.",
        "select_players_to_include": "Sélectionnez les joueurs à inclure",
        "excluded_players_caption": "Ces joueurs sont actuellement exclus de l’analyse du groupe sélectionné.",
        "selected_group_impact": "2. Impact du groupe sélectionné",
        "selected_group_impact_caption": "Cette section présente les résultats combinés des joueurs sélectionnés selon les filtres actuels de la barre latérale.",
        "positive_negative_net_contribution": "3. Contributions nettes positives et négatives",
        "score_balance_caption": "Le graphique de gauche montre tous les joueurs correspondant aux filtres actuels de la barre latérale. Le graphique de droite montre uniquement les joueurs sélectionnés après les exclusions.",
        "before_exclusion": "**Avant les exclusions**",
        "before_exclusion_caption": "Tous les joueurs correspondant aux filtres actuels de la barre latérale.",
        "after_exclusion": "**Après les exclusions**",
        "after_exclusion_caption": "Seuls les joueurs sélectionnés sont affichés. Les joueurs exclus ne sont pas inclus dans ce graphique.",
        "alliance_impact_selected_players": "4. Impact des joueurs sélectionnés sur les alliances",
        "alliance_impact_selected_players_caption": "Cette section montre la contribution des joueurs sélectionnés à chaque alliance. Elle affiche les résultats complets d’une alliance uniquement lorsque tous ses joueurs sont sélectionnés.",
        "no_players_selected_alliance_summary": "Aucun joueur n’est sélectionné. Sélectionnez au moins un joueur pour afficher le résumé par alliance."
    },
    "vi": {
        "app_title": "Bảng điều khiển điểm SVS",
        "app_caption": "Khám phá tác động của người chơi và liên minh đến kết quả SVS của Máy chủ 559+461.",
        "filters": "Bộ lọc",
        "language": "Ngôn ngữ",
        "svs_period": "Kỳ SVS",
        "select_alliances": "Chọn liên minh",
        "select_net_status": "Chọn trạng thái ròng",
        "sidebar_caption": "Bộ lọc ảnh hưởng đến tất cả biểu đồ và bảng dữ liệu. Các chỉ số Tổng quan hiển thị tổng số toàn máy chủ của kỳ SVS đã chọn.",
        "overview": "Tổng quan",
        "alliance_summary": "Tóm tắt liên minh",
        "alliance_summary_caption": "So sánh điểm kiếm được, điểm bị mất, điểm ròng và số lượng người chơi giữa các liên minh.",
        "player_data": "Dữ liệu người chơi",
        "player_data_caption": "Dữ liệu SVS cấp người chơi đã được lọc và sử dụng trong các biểu đồ và phân tích.",
        "player_rankings": "Xếp hạng người chơi",
        "select_ranking_view": "Chọn chế độ xếp hạng",
        "top_10_net_score": "Top 10 điểm ròng",
        "bottom_10_net_score": "10 người có điểm ròng thấp nhất",
        "top_10_score_gained": "Top 10 điểm kiếm được",
        "top_10_score_lost": "Top 10 điểm bị mất",
        "contribution_insight": "Phân tích đóng góp",
        "contribution_insight_caption": "Xem cách các liên minh được chọn đóng góp vào kết quả SVS tích cực và tiêu cực.",
        "contribution_share": "### Tỷ lệ đóng góp",
        "contribution_share_caption": "Tỷ lệ đóng góp dương cho thấy liên minh nào tạo ra điểm ròng dương. Tỷ lệ đóng góp âm cho thấy liên minh nào tạo ra điểm ròng âm.",
        "positive_contribution": "**Đóng góp tích cực**",
        "negative_contribution": "**Đóng góp tiêu cực**",
        "positive_side": "**Phía tích cực**",
        "negative_side": "**Phía tiêu cực**",
        "contribution_details": "### Chi tiết đóng góp",
        "contribution_details_caption": "Các bảng hiển thị các giá trị chính xác được thể hiện trong biểu đồ tròn.",
        "no_positive_net_score": "Không tìm thấy điểm ròng dương trong dữ liệu đã chọn.",
        "no_negative_net_score": "Không tìm thấy điểm ròng âm trong dữ liệu đã chọn.",
        "negative_chart_explanation": "Biểu đồ âm sử dụng giá trị tuyệt đối để thể hiện tỷ lệ đóng góp của từng liên minh vào tổng tác động tiêu cực.",
        "player_selection_insight": "Phân tích lựa chọn người chơi",
        "player_selection_insight_caption": "Sử dụng tab này để xem việc thêm hoặc loại bỏ người chơi làm thay đổi kết quả đã lọc ở cấp máy chủ và phần tóm tắt theo liên minh như thế nào.",
        "score": "Điểm",
        "score_gained": "Điểm kiếm được",
        "score_lost": "Điểm bị mất",
        "net_score": "Điểm ròng",
        "svs_rank": "Xếp hạng SVS",
        "players": "Người chơi",
        "alliance": "Liên minh",
        "player": "Người chơi",
        "filtered_players": "Người chơi đã lọc",
        "selected_players": "Người chơi được chọn",
        "excluded_players": "Người chơi bị loại",
        "no_excluded_players": "Không có người chơi nào bị loại. Tất cả người chơi đã lọc hiện đều được đưa vào phân tích.",
        "positive": "Dương",
        "negative": "Âm",
        "positive_players": "Người chơi dương",
        "negative_players": "Người chơi âm",
        "total_net_score": "Tổng điểm ròng",
        "net_per_player": "Điểm ròng mỗi người chơi",
        "ranking_chart_guide":
        """
        **Cách sử dụng:** Theo mặc định, biểu đồ xếp hạng so sánh những người chơi thuộc các liên minh hiện đang được chọn trên thanh bên. Để xem bảng xếp hạng người chơi trên toàn máy chủ, hãy mở bộ lọc liên minh và chọn **Select all**.
        """,
        "status": "Trạng thái",
        "score_gained_vs_net_score": "Điểm kiếm được so với Điểm ròng",
        "scatter_chart_caption": "Mỗi điểm đại diện cho một người chơi. Các điểm nằm trên 0 thể hiện điểm ròng dương, trong khi các điểm nằm dưới 0 thể hiện điểm ròng âm.",
        "total_net_score_by_alliance": "Tổng điểm ròng theo liên minh",
        "total_net_score_by_alliance_caption": "So sánh tổng điểm ròng giữa các liên minh dựa trên các bộ lọc hiện tại.",
        "net_score_per_player_by_alliance": "Điểm ròng mỗi người chơi theo liên minh",
        "net_score_per_player_by_alliance_caption": "So sánh điểm ròng trung bình mỗi người chơi giữa các liên minh. Điều này giúp cân bằng việc so sánh giữa các liên minh lớn và nhỏ.",
        "positive_net": "Điểm ròng dương",
        "negative_net": "Điểm ròng âm",
        "zero_net_score": "Điểm ròng bằng 0",
        "share": "Tỷ lệ",
        "share_percent": "Tỷ lệ (%)",
        "contribution_reading_guide":
        """
        **Cách đọc phần này:**
        Tỷ lệ đóng góp dương cho biết những liên minh nào đã tạo ra điểm ròng dương của máy chủ.
        Tỷ lệ đóng góp âm cho biết những liên minh nào đã tạo ra điểm ròng âm của máy chủ.
        Các kết quả này phản ánh các bộ lọc hiện tại trên thanh bên.
        """,
        "choose_players_to_include": "1. Chọn người chơi để đưa vào phân tích",
        "choose_players_caption": "Những người chơi được chọn sẽ được đưa vào phân tích. Hãy loại bớt người chơi để xem kết quả thay đổi như thế nào khi không có họ.",
        "select_players_to_include": "Chọn người chơi để đưa vào phân tích",
        "excluded_players_caption": "Những người chơi này hiện đang bị loại khỏi phần phân tích nhóm đã chọn.",
        "selected_group_impact": "2. Tác động của nhóm đã chọnt",
        "selected_group_impact_caption": "Phần này hiển thị kết quả tổng hợp của những người chơi đã chọn trong phạm vi các bộ lọc hiện tại trên thanh bên.",
        "positive_negative_net_contribution": "3. Đóng góp ròng dương và âm",
        "score_balance_caption": "Biểu đồ bên trái hiển thị tất cả người chơi thuộc phạm vi các bộ lọc hiện tại trên thanh bên. Biểu đồ bên phải chỉ hiển thị những người chơi được chọn sau khi loại người chơi.",
        "before_exclusion": "**Trước khi loại người chơi**",
        "before_exclusion_caption": "Tất cả người chơi thuộc phạm vi các bộ lọc hiện tại trên thanh bên.",
        "after_exclusion": "**Sau khi loại người chơi**",
        "after_exclusion_caption": "Chỉ hiển thị những người chơi được chọn. Những người chơi bị loại không được đưa vào biểu đồ này.",
        "alliance_impact_selected_players": "4. Tác động của người chơi được chọn đối với các liên minh",
        "alliance_impact_selected_players_caption": "Phần này cho biết những người chơi được chọn đóng góp như thế nào cho từng liên minh. Kết quả đầy đủ của một liên minh chỉ được hiển thị khi tất cả người chơi của liên minh đó đều được chọn.",
        "no_players_selected_alliance_summary": "Chưa có người chơi nào được chọn. Hãy chọn ít nhất một người chơi để hiển thị phần tóm tắt theo liên minh."
    },
    "id": {
        "app_title": "Dasbor Skor SVS",
        "app_caption": "Jelajahi dampak pemain dan aliansi terhadap hasil SVS untuk Server 559+461.",
        "filters": "Filter",
        "language": "Bahasa",
        "svs_period": "Periode SVS",
        "select_alliances": "Pilih aliansi",
        "select_net_status": "Pilih status bersih",
        "sidebar_caption": "Filter memengaruhi semua grafik dan tabel. Metrik Ringkasan menampilkan total keseluruhan server untuk periode SVS yang dipilih.",
        "overview": "Ringkasan",
        "alliance_summary": "Ringkasan Aliansi",
        "alliance_summary_caption": "Bandingkan poin yang diperoleh, poin yang hilang, poin bersih, dan jumlah pemain antaraliansi.",
        "player_data": "Data Pemain",
        "player_data_caption": "Data SVS tingkat pemain yang telah difilter dan digunakan dalam grafik serta analisis",
        "player_rankings": "Peringkat Pemain",
        "select_ranking_view": "Pilih tampilan peringkat",
        "top_10_net_score": "10 Teratas berdasarkan Poin Bersih",
        "bottom_10_net_score": "10 Terbawah berdasarkan Poin Bersih",
        "top_10_score_gained": "10 Teratas berdasarkan Poin yang Diperoleh",
        "top_10_score_lost": "10 Teratas berdasarkan Poin yang Hilang",
        "contribution_insight": "Analisis Kontribusi",
        "contribution_insight_caption": "Lihat bagaimana aliansi yang dipilih berkontribusi terhadap hasil SVS positif dan negatif.",
        "contribution_share": "### Persentase Kontribusi",
        "contribution_share_caption": "Persentase positif menunjukkan aliansi mana yang menghasilkan poin bersih positif. Persentase negatif menunjukkan aliansi mana yang menghasilkan poin bersih negatif.",
        "positive_contribution": "**Kontribusi Positif**",
        "negative_contribution": "**Kontribusi Negatif**",
        "positive_side": "**Sisi Positif**",
        "negative_side": "**Sisi Negatif**",
        "contribution_details": "### Rincian Kontribusi",
        "contribution_details_caption": "Tabel menampilkan nilai pasti yang digunakan dalam diagram lingkaran.",
        "no_positive_net_score": "Tidak ditemukan poin bersih positif dalam data yang dipilih.",
        "no_negative_net_score": "Tidak ditemukan poin bersih negatif dalam data yang dipilih.",
        "negative_chart_explanation": "Grafik negatif menggunakan nilai absolut untuk menunjukkan persentase kontribusi setiap aliansi terhadap total dampak negatif.",
        "player_selection_insight": "Analisis Pemilihan Pemain",
        "player_selection_insight_caption": "Gunakan tab ini untuk melihat bagaimana penambahan atau penghapusan pemain mengubah hasil tingkat server yang telah difilter dan ringkasan tingkat aliansi.",
        "score": "Poin",
        "score_gained": "Poin yang Diperoleh",
        "score_lost": "Poin yang Hilang",
        "net_score": "Poin Bersih",
        "svs_rank": "Peringkat SVS",
        "players": "Pemain",
        "alliance": "Aliansi",
        "player": "Pemain",
        "filtered_players": "Pemain yang Difilter",
        "selected_players": "Pemain yang Dipilih",
        "excluded_players": "Pemain yang Dikecualikan",
        "no_excluded_players": "Tidak ada pemain yang dikecualikan. Semua pemain yang telah difilter saat ini disertakan.",
        "positive": "Positif",
        "negative": "Negatif",
        "positive_players": "Pemain dengan Poin Bersih Positif",
        "negative_players": "Pemain dengan Poin Bersih Negatif",
        "total_net_score": "Total Poin Bersih",
        "net_per_player": "Poin Bersih per Pemain",
        "ranking_chart_guide":
        """
        **Cara menggunakan:**
        Secara default, grafik peringkat membandingkan pemain dari aliansi yang saat ini dipilih di bilah sisi. Untuk melihat peringkat pemain di seluruh server, buka filter aliansi lalu pilih **Select all**.
        """,
        "status": "Status",
        "score_gained_vs_net_score": "Poin yang Diperoleh vs Poin Bersih",
        "scatter_chart_caption": "Setiap titik mewakili satu pemain. Titik di atas nol menunjukkan poin bersih positif, sedangkan titik di bawah nol menunjukkan poin bersih negatif.",
        "total_net_score_by_alliance": "Total Poin Bersih berdasarkan Aliansi",
        "total_net_score_by_alliance_caption": "Bandingkan total poin bersih antaraliansi berdasarkan filter saat ini.",
        "net_score_per_player_by_alliance": "Poin Bersih per Pemain berdasarkan Aliansi",
        "net_score_per_player_by_alliance_caption": "Bandingkan rata-rata poin bersih per pemain antaraliansi. Ini membantu menyeimbangkan perbandingan antara aliansi besar dan kecil.",
        "positive_net": "Poin Bersih Positif",
        "negative_net": "Poin Bersih Negatif",
        "zero_net_score": "Poin Bersih Nol",
        "share": "Persentase",
        "share_percent": "Persentase (%)",
        "contribution_reading_guide":
        """
        **Cara membaca bagian ini:**
        Persentase Kontribusi Positif menunjukkan aliansi mana yang menghasilkan poin bersih positif server.
        Persentase Kontribusi Negatif menunjukkan aliansi mana yang menghasilkan poin bersih negatif server.
        Hasil ini mencerminkan filter bilah sisi yang sedang digunakan.
        """,
        "choose_players_to_include": "1. Pilih Pemain yang Akan Disertakan",
        "choose_players_caption": "Pemain yang dipilih akan disertakan dalam analisis. Keluarkan pemain dari pilihan untuk melihat bagaimana hasil berubah tanpa mereka.",
        "select_players_to_include": "Pilih pemain yang akan disertakan",
        "excluded_players_caption": "Pemain ini saat ini dikecualikan dari analisis kelompok yang dipilih.",
        "selected_group_impact": "2. Dampak Kelompok yang Dipilih",
        "selected_group_impact_caption": "Bagian ini menampilkan hasil gabungan dari para pemain yang dipilih berdasarkan filter bilah sisi saat ini.",
        "positive_negative_net_contribution": "3. Kontribusi Bersih Positif dan Negatif",
        "score_balance_caption": "Grafik sebelah kiri menampilkan semua pemain yang termasuk dalam filter bilah sisi saat ini. Grafik sebelah kanan hanya menampilkan pemain yang dipilih setelah pengecualian.",
        "before_exclusion": "**Sebelum Pengecualian**",
        "before_exclusion_caption": "Semua pemain yang termasuk dalam filter bilah sisi saat ini.",
        "after_exclusion": "**Setelah Pengecualian**",
        "after_exclusion_caption": "Hanya pemain yang dipilih. Pemain yang dikecualikan tidak disertakan dalam grafik ini.",
        "alliance_impact_selected_players": "4. Dampak Pemain yang Dipilih terhadap Aliansi",
        "alliance_impact_selected_players_caption": "Bagian ini menunjukkan kontribusi pemain yang dipilih terhadap setiap aliansi. Hasil lengkap suatu aliansi hanya ditampilkan apabila semua pemainnya dipilih.",
        "no_players_selected_alliance_summary": "Tidak ada pemain yang dipilih. Pilih setidaknya satu pemain untuk menampilkan ringkasan aliansi."
    }
}

def t(key):
    lang = st.session_state.get("lang", "en")
    return TEXT.get(lang, {}).get(key, TEXT["en"].get(key, key))

# Page settings
st.set_page_config(
    page_title="SVS Scores Dashboard",
    layout="wide"
)

# Load data
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)

    # Clean data
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df = df.dropna(how="all")

    # Make sure score columns are numeric
    score_columns = ["score_gained", "score_lost", "net_score", "competition_rank"]

    for col in score_columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

df = load_data("svs_scores_utf8.csv")

# Page title
st.title(t("app_title"))
st.caption(t("app_caption"))

# Fuction: make alliance summary
def make_alliance_summary(data):
    alliance_summary = (
        data
        .groupby("alliance", as_index=False)
        .agg(
            players=("player_name", "nunique"),
            positive_players=("net_status", lambda x: (x.astype(str).str.lower() == "positive").sum()),
            negative_players=("net_status", lambda x: (x.astype(str).str.lower() == "negative").sum()),
            total_score_gained=("score_gained", "sum"),
            total_score_lost=("score_lost", "sum"),
            total_net_score=("net_score", "sum"),
            average_net_score=("net_score", "mean")
        )
        .sort_values("total_net_score", ascending=False)
    )

    return alliance_summary

# Fuction: translate net status filter
def translate_net_status(status):
    status_key = str(status).strip().lower()

    status_keys = {
        "positive": "positive",
        "negative": "negative",
    }

    return t(status_keys.get(status_key, status_key))

# -----------------------------
# Language setup
# -----------------------------
if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

def update_language():
    st.session_state["lang"] = LANGUAGES[st.session_state["selected_language"]]

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header(t("filters"))

selected_language = st.sidebar.selectbox(
    "Language/Idioma/Langue/Ngôn ngữ/Bahasa",
    options=list(LANGUAGES.keys()),
    index=list(LANGUAGES.values()).index(st.session_state["lang"]),
    key="selected_language",
    on_change=update_language
)

# SVS period
# Sort newest first. Values such as 2026-W25 sort correctly in descending order.
svs_options = sorted(
    df["svs_date"].dropna().astype(str).unique(),
    reverse=True
)

selected_svs = st.sidebar.selectbox(
    t("svs_period"),
    options=svs_options,
    index=0,
    key="selected_svs"
)

# Keep a dedicated full-server dataset for the selected SVS period.
# Overview metrics use this dataset, while the other tabs use filtered_df below.
period_df = df[df["svs_date"].astype(str) == selected_svs].copy()

# Alliance selection: only show alliances present in the selected period.
alliance_options = sorted(period_df["alliance"].dropna().unique())

default_alliances = [
    a for a in ["SnS", "NoM", "TDA", "MBV"]
    if a in alliance_options
]

selected_alliances = st.sidebar.multiselect(
    t("select_alliances"),
    options=alliance_options,
    default=default_alliances if default_alliances else alliance_options
)

# Net status selection: only show statuses present in the selected period.
net_status_options = sorted(period_df["net_status"].dropna().unique())

selected_net_status = st.sidebar.multiselect(
    t("select_net_status"),
    options=net_status_options,
    default=net_status_options,
    format_func=translate_net_status
)

st.sidebar.caption(t("sidebar_caption"))

filtered_df = period_df[
    (period_df["alliance"].isin(selected_alliances)) &
    (period_df["net_status"].isin(selected_net_status))
].copy()

# Ask the Dashboard
QUESTION_NET_VS_POSITIVE = (
    "Why does the top net-score alliance rank second in positive contribution?"
)
QUESTION_EXCLUSION_IMPACT = (
    "What changed after excluding the selected players?"
)
QUESTION_NEGATIVE_PERCENTAGE = (
    "Why did the negative percentage increase?"
)
QUESTION_TOP_CONTRIBUTORS = (
    "Which players contributed most to the selected alliance?"
)
QUESTION_CUSTOM = "Write my own question"

SUGGESTED_QUESTIONS = [
    QUESTION_NET_VS_POSITIVE,
    QUESTION_EXCLUSION_IMPACT,
    QUESTION_NEGATIVE_PERCENTAGE,
    QUESTION_TOP_CONTRIBUTORS,
    QUESTION_CUSTOM,
]


def format_score(value):
    """Format dashboard scores consistently for narrative answers."""
    return f"{value:,.0f}"


def format_signed_score(value):
    """Format a score change with an explicit plus or minus sign."""
    if value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


def get_current_selected_player_names(data):
    """Return the Player Selection tab's current included-player list."""
    if "player_name" not in data.columns:
        return []

    available_players = sorted(
        data["player_name"].dropna().unique().tolist()
    )
    stored_selection = st.session_state.get(
        "dashboard_selected_players"
    )

    # Before the Player Selection widget has been rendered, its intended
    # default is to include every player in the current filtered scope.
    if stored_selection is None:
        return available_players

    available_set = set(available_players)
    return [
        player for player in stored_selection
        if player in available_set
    ]



def normalize_question_text(question):
    """Normalize free-text questions for simple rule-based routing."""
    normalized = unicodedata.normalize("NFKC", str(question)).casefold()
    normalized = re.sub(r"[^\w\s%+-]", " ", normalized)
    return " ".join(normalized.split())


def extract_alliance_names_from_question(question, alliance_names):
    """Find alliance names mentioned in a question, case-insensitively."""
    question_text = unicodedata.normalize(
        "NFKC",
        str(question),
    ).casefold()

    matches = []
    for alliance in sorted(
        {str(name) for name in alliance_names if pd.notna(name)},
        key=len,
        reverse=True,
    ):
        alliance_text = unicodedata.normalize(
            "NFKC",
            alliance,
        ).casefold()

        # Boundaries prevent short alliance names from matching inside words.
        pattern = rf"(?<!\w){re.escape(alliance_text)}(?!\w)"
        if re.search(pattern, question_text):
            matches.append(alliance)

    return matches


def explain_total_net_excluding_alliances(
    data,
    excluded_alliances,
    svs_period=None,
):
    """Calculate total net score before and after excluding alliances."""
    required_columns = {
        "alliance",
        "player_name",
        "score_gained",
        "score_lost",
        "net_score",
    }
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This calculation cannot be completed because the current data "
            f"is missing: {missing_text}."
        )

    if not excluded_alliances:
        return (
            "I understood that you want to exclude an alliance, but I could "
            "not identify its name. Include an alliance name in the question, "
            "for example: **What is the total net score without TDA?**"
        )

    working_df = data[
        [
            "alliance",
            "player_name",
            "score_gained",
            "score_lost",
            "net_score",
        ]
    ].copy()

    for column in ["score_gained", "score_lost", "net_score"]:
        working_df[column] = pd.to_numeric(
            working_df[column],
            errors="coerce",
        )

    working_df = working_df.dropna(subset=["alliance", "net_score"])

    if working_df.empty:
        return (
            "There is no score data in the current filter scope. Select at "
            "least one alliance and net-status option, then try again."
        )

    requested_lookup = {
        str(name).casefold(): str(name)
        for name in excluded_alliances
    }
    in_scope_lookup = {
        str(name).casefold(): str(name)
        for name in working_df["alliance"].dropna().unique()
    }

    recognized_in_scope = [
        in_scope_lookup[key]
        for key in requested_lookup
        if key in in_scope_lookup
    ]
    outside_scope = [
        requested_lookup[key]
        for key in requested_lookup
        if key not in in_scope_lookup
    ]

    before_net = working_df["net_score"].sum()
    before_players = working_df["player_name"].nunique()

    if not recognized_in_scope:
        outside_text = ", ".join(f"**{name}**" for name in outside_scope)
        return (
            f"{outside_text} is not included in the current alliance filter, "
            f"so excluding it does not change the current total net score of "
            f"**{format_signed_score(before_net)}**. Add the alliance to the "
            "sidebar selection first if you want a before-and-after comparison."
        )

    excluded_mask = working_df["alliance"].astype(str).str.casefold().isin(
        {name.casefold() for name in recognized_in_scope}
    )
    excluded_df = working_df[excluded_mask].copy()
    remaining_df = working_df[~excluded_mask].copy()

    excluded_net = excluded_df["net_score"].sum()
    excluded_gained = excluded_df["score_gained"].sum()
    excluded_lost = excluded_df["score_lost"].sum()
    after_net = remaining_df["net_score"].sum()
    net_change = after_net - before_net
    after_players = remaining_df["player_name"].nunique()

    alliance_text = ", ".join(
        f"**{name}**" for name in recognized_in_scope
    )
    period_text = f" for **{svs_period}**" if svs_period else ""

    if excluded_net < 0:
        interpretation = (
            "The total improves because the excluded alliance group had a "
            "negative net contribution in this scope."
        )
    elif excluded_net > 0:
        interpretation = (
            "The total decreases because the excluded alliance group had a "
            "positive net contribution in this scope."
        )
    else:
        interpretation = (
            "The total does not change because the excluded alliance group "
            "had a net contribution of zero in this scope."
        )

    outside_note = ""
    if outside_scope:
        outside_note = (
            "\n\nThe following named alliance(s) were already outside the "
            "current filter and therefore had no additional effect: "
            + ", ".join(f"**{name}**" for name in outside_scope)
            + "."
        )

    return (
        f"Within the current dashboard filters{period_text}, excluding "
        f"{alliance_text} changes total net score from "
        f"**{format_signed_score(before_net)}** to "
        f"**{format_signed_score(after_net)}** "
        f"(**{format_signed_score(net_change)}**).\n\n"
        f"The excluded alliance group contributed:\n"
        f"- Score gained: **{format_score(excluded_gained)}**\n"
        f"- Score lost: **{format_score(excluded_lost)}**\n"
        f"- Net score: **{format_signed_score(excluded_net)}**\n\n"
        f"Players remaining: **{after_players}/{before_players}**. "
        f"{interpretation}{outside_note}"
    )

def explain_net_vs_positive_ranking(data, svs_period=None):
    """
    Explain why the alliance with the highest total net score may rank lower
    in positive contribution.

    Positive contribution = sum of positive player net scores.
    Negative impact = absolute sum of negative player net scores.
    Total net score = positive contribution - negative impact.
    """
    required_columns = {"alliance", "net_score"}
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_df = data[["alliance", "net_score"]].copy()
    working_df["net_score"] = pd.to_numeric(
        working_df["net_score"],
        errors="coerce"
    )
    working_df = working_df.dropna(subset=["alliance", "net_score"])

    if working_df.empty:
        return (
            "There is no score data in the current filter scope. "
            "Select at least one alliance and net status, then try again."
        )

    alliance_count = working_df["alliance"].nunique()
    if alliance_count < 2:
        return (
            "This comparison needs at least two alliances in the current "
            "filter scope. Select more alliances and try again."
        )

    # This question depends on both the positive and negative sides.
    if "net_status" in data.columns:
        status_values = {
            str(value).strip().lower()
            for value in data["net_status"].dropna().unique()
        }
        if not {"positive", "negative"}.issubset(status_values):
            return (
                "This question is intended to compare positive contribution "
                "with negative impact, but the current Net Status filter does "
                "not include both Positive and Negative. Select both statuses "
                "to get the full explanation."
            )

    alliance_analysis = (
        working_df
        .groupby("alliance", as_index=False)
        .agg(
            total_net_score=("net_score", "sum"),
            positive_net_score=(
                "net_score",
                lambda scores: scores[scores > 0].sum()
            ),
            negative_impact=(
                "net_score",
                lambda scores: scores[scores < 0].abs().sum()
            ),
        )
    )

    alliance_analysis["net_rank"] = (
        alliance_analysis["total_net_score"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    alliance_analysis["positive_rank"] = (
        alliance_analysis["positive_net_score"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    top_net_rows = alliance_analysis[
        alliance_analysis["net_rank"] == 1
    ].copy()

    if len(top_net_rows) > 1:
        tied_alliances = ", ".join(
            sorted(top_net_rows["alliance"].astype(str))
        )
        tied_score = top_net_rows["total_net_score"].iloc[0]
        return (
            "The current filters produce a tie for first place in total net "
            f"score: {tied_alliances}, each with {format_score(tied_score)}. "
            "Because there is no single top net-score alliance, the premise "
            "of this question does not currently apply."
        )

    top_net = top_net_rows.iloc[0]
    top_name = str(top_net["alliance"])
    positive_rank = int(top_net["positive_rank"])

    positive_leaders = alliance_analysis[
        alliance_analysis["positive_rank"] == 1
    ].copy()

    # If the net leader is also a positive-contribution leader, explain that
    # the suggested question does not match the current filtered data.
    if positive_rank == 1:
        period_text = f" for {svs_period}" if svs_period else ""
        return (
            f"The premise does not match the current filtered data{period_text}. "
            f"**{top_name}** ranks first in both total net score "
            f"({format_score(top_net['total_net_score'])}) and positive "
            f"contribution ({format_score(top_net['positive_net_score'])})."
        )

    # Compare the net leader with one of the alliances leading positive
    # contribution. Sorting by total net score makes the comparison stable
    # if more than one alliance is tied for the positive lead.
    positive_leader = (
        positive_leaders
        .sort_values("total_net_score", ascending=False)
        .iloc[0]
    )
    positive_leader_name = str(positive_leader["alliance"])

    positive_gap = (
        positive_leader["positive_net_score"]
        - top_net["positive_net_score"]
    )
    negative_advantage = (
        positive_leader["negative_impact"]
        - top_net["negative_impact"]
    )
    net_lead = (
        top_net["total_net_score"]
        - positive_leader["total_net_score"]
    )

    period_text = f" in {svs_period}" if svs_period else ""
    rank_statement = (
        "second"
        if positive_rank == 2
        else f"#{positive_rank}, not second"
    )

    explanation = (
        f"Under the current sidebar filters{period_text}, **{top_name}** "
        f"ranks first in total net score with "
        f"**{format_score(top_net['total_net_score'])}**, while it ranks "
        f"{rank_statement} in positive contribution with "
        f"**{format_score(top_net['positive_net_score'])}**.\n\n"
        f"**{positive_leader_name}** leads positive contribution with "
        f"**{format_score(positive_leader['positive_net_score'])}**, which is "
        f"**{format_score(positive_gap)}** more than {top_name}. However, "
        f"{positive_leader_name}'s negative impact is "
        f"**{format_score(positive_leader['negative_impact'])}**, compared "
        f"with **{format_score(top_net['negative_impact'])}** for {top_name}. "
        f"That gives {top_name} a **{format_score(negative_advantage)}** "
        f"advantage from losing fewer points.\n\n"
        f"The lower negative impact offsets the smaller positive contribution, "
        f"leaving {top_name} ahead of {positive_leader_name} by "
        f"**{format_score(net_lead)}** in total net score. Here, positive "
        f"contribution is the sum of positive player net scores, and total "
        f"net score equals positive contribution minus negative impact."
    )

    return explanation


def explain_exclusion_impact(
    data,
    selected_player_names=None,
    svs_period=None,
):
    """Explain the before/after effect of the current player exclusions."""
    required_columns = {
        "player_name",
        "score_gained",
        "score_lost",
        "net_score",
    }
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_df = data[
        ["player_name", "score_gained", "score_lost", "net_score"]
    ].copy()

    for column in ["score_gained", "score_lost", "net_score"]:
        working_df[column] = pd.to_numeric(
            working_df[column],
            errors="coerce",
        )

    working_df = working_df.dropna(
        subset=["player_name", "net_score"]
    )

    if working_df.empty:
        return (
            "There is no player score data in the current filter scope. "
            "Select at least one alliance and net status, then try again."
        )

    all_player_names = sorted(
        working_df["player_name"].dropna().unique().tolist()
    )

    if selected_player_names is None:
        selected_player_names = all_player_names

    valid_players = set(all_player_names)
    selected_player_names = [
        player for player in selected_player_names
        if player in valid_players
    ]

    selected_df = working_df[
        working_df["player_name"].isin(selected_player_names)
    ].copy()
    excluded_df = working_df[
        ~working_df["player_name"].isin(selected_player_names)
    ].copy()

    before_player_count = working_df["player_name"].nunique()
    after_player_count = selected_df["player_name"].nunique()
    excluded_player_names = sorted(
        excluded_df["player_name"].dropna().unique().tolist()
    )
    excluded_player_count = len(excluded_player_names)

    period_text = f" in {svs_period}" if svs_period else ""

    if excluded_player_count == 0:
        before_net = working_df["net_score"].sum()
        return (
            f"No players are currently excluded from the filtered group"
            f"{period_text}. The before-and-after results are therefore "
            f"identical: **{before_player_count} players** with a total net "
            f"score of **{format_score(before_net)}**. Remove at least one "
            "player in the Player Selection Insight tab to compare the "
            "impact."
        )

    def calculate_metrics(frame):
        positive_contribution = frame.loc[
            frame["net_score"] > 0,
            "net_score",
        ].sum()
        negative_impact = frame.loc[
            frame["net_score"] < 0,
            "net_score",
        ].abs().sum()

        return {
            "score_gained": frame["score_gained"].sum(),
            "score_lost": frame["score_lost"].sum(),
            "net_score": frame["net_score"].sum(),
            "positive_contribution": positive_contribution,
            "negative_impact": negative_impact,
        }

    before = calculate_metrics(working_df)
    after = calculate_metrics(selected_df)

    changes = {
        key: after[key] - before[key]
        for key in before
    }

    positive_removed = (
        before["positive_contribution"]
        - after["positive_contribution"]
    )
    negative_removed = (
        before["negative_impact"]
        - after["negative_impact"]
    )
    net_change = changes["net_score"]

    if net_change > 0:
        outcome = (
            f"The total net score **improved by "
            f"{format_score(net_change)}**. The exclusions removed "
            f"**{format_score(negative_removed)}** of negative impact but "
            f"only **{format_score(positive_removed)}** of positive "
            "contribution, so the reduction in losses was greater than the "
            "reduction in gains."
        )
    elif net_change < 0:
        outcome = (
            f"The total net score **decreased by "
            f"{format_score(abs(net_change))}**. The exclusions removed "
            f"**{format_score(positive_removed)}** of positive contribution "
            f"but only **{format_score(negative_removed)}** of negative "
            "impact, so more useful contribution was removed than harmful "
            "impact."
        )
    else:
        outcome = (
            "The total net score did not change. The removed positive "
            f"contribution (**{format_score(positive_removed)}**) and removed "
            f"negative impact (**{format_score(negative_removed)}**) offset "
            "each other exactly."
        )

    if excluded_player_count <= 5:
        excluded_text = ", ".join(
            map(str, excluded_player_names)
        )
    else:
        preview = ", ".join(
            map(str, excluded_player_names[:5])
        )
        excluded_text = (
            f"{preview}, and {excluded_player_count - 5} others"
        )

    return (
        f"After the current exclusions{period_text}, the analysis includes "
        f"**{after_player_count} of {before_player_count} players**. "
        f"**Excluded:** {excluded_text}.\n\n"
        f"- **Score gained:** {format_score(before['score_gained'])} → "
        f"{format_score(after['score_gained'])} "
        f"({format_signed_score(changes['score_gained'])})\n"
        f"- **Score lost:** {format_score(before['score_lost'])} → "
        f"{format_score(after['score_lost'])} "
        f"({format_signed_score(changes['score_lost'])})\n"
        f"- **Positive contribution:** "
        f"{format_score(before['positive_contribution'])} → "
        f"{format_score(after['positive_contribution'])} "
        f"({format_signed_score(changes['positive_contribution'])})\n"
        f"- **Negative impact:** "
        f"{format_score(before['negative_impact'])} → "
        f"{format_score(after['negative_impact'])} "
        f"({format_signed_score(changes['negative_impact'])})\n"
        f"- **Total net score:** {format_score(before['net_score'])} → "
        f"{format_score(after['net_score'])} "
        f"({format_signed_score(net_change)})\n\n"
        f"{outcome}"
    )


def explain_negative_percentage_change(
    data,
    selected_player_names=None,
    svs_period=None,
):
    """Explain how player exclusions changed the negative-score share."""
    required_columns = {"player_name", "net_score"}
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_columns = ["player_name", "net_score"]
    if "net_status" in data.columns:
        working_columns.append("net_status")

    working_df = data[working_columns].copy()
    working_df["net_score"] = pd.to_numeric(
        working_df["net_score"],
        errors="coerce",
    )
    working_df = working_df.dropna(
        subset=["player_name", "net_score"]
    )

    if working_df.empty:
        return (
            "There is no player score data in the current filter scope. "
            "Select at least one alliance and net status, then try again."
        )

    # A positive-versus-negative percentage is only meaningful when both
    # sides are included in the current scope.
    if "net_status" in working_df.columns:
        status_values = {
            str(value).strip().lower()
            for value in working_df["net_status"].dropna().unique()
        }
        if not {"positive", "negative"}.issubset(status_values):
            return (
                "This question compares the positive and negative sides, but "
                "the current Net Status filter does not include both Positive "
                "and Negative. Select both statuses and try again."
            )

    all_player_names = sorted(
        working_df["player_name"].dropna().unique().tolist()
    )

    if selected_player_names is None:
        selected_player_names = all_player_names

    valid_players = set(all_player_names)
    selected_player_names = [
        player for player in selected_player_names
        if player in valid_players
    ]

    selected_df = working_df[
        working_df["player_name"].isin(selected_player_names)
    ].copy()
    excluded_df = working_df[
        ~working_df["player_name"].isin(selected_player_names)
    ].copy()

    excluded_player_names = sorted(
        excluded_df["player_name"].dropna().unique().tolist()
    )
    excluded_player_count = len(excluded_player_names)
    period_text = f" in {svs_period}" if svs_period else ""

    def calculate_balance(frame):
        positive = frame.loc[
            frame["net_score"] > 0,
            "net_score",
        ].sum()
        negative = frame.loc[
            frame["net_score"] < 0,
            "net_score",
        ].abs().sum()
        total_magnitude = positive + negative
        negative_share = (
            negative / total_magnitude * 100
            if total_magnitude > 0
            else None
        )
        return {
            "positive": positive,
            "negative": negative,
            "total_magnitude": total_magnitude,
            "negative_share": negative_share,
        }

    before = calculate_balance(working_df)
    after = calculate_balance(selected_df)

    if before["negative_share"] is None:
        return (
            "The negative percentage cannot be calculated because the "
            "current filtered group has no positive or negative net-score "
            "magnitude."
        )

    if excluded_player_count == 0:
        return (
            f"No players are currently excluded from the filtered group"
            f"{period_text}. The negative share is unchanged at "
            f"**{before['negative_share']:.1f}%**. Remove at least one "
            "player in the Player Selection Insight tab to create a "
            "before-and-after comparison."
        )

    if after["negative_share"] is None:
        return (
            f"After the current exclusions{period_text}, no score magnitude "
            "remains in the selected group, so an after-exclusion negative "
            "percentage cannot be calculated."
        )

    share_change = (
        after["negative_share"] - before["negative_share"]
    )
    positive_removed = before["positive"] - after["positive"]
    negative_removed = before["negative"] - after["negative"]

    positive_reduction_rate = (
        positive_removed / before["positive"] * 100
        if before["positive"] > 0
        else 0
    )
    negative_reduction_rate = (
        negative_removed / before["negative"] * 100
        if before["negative"] > 0
        else 0
    )

    if excluded_player_count <= 5:
        excluded_text = ", ".join(map(str, excluded_player_names))
    else:
        preview = ", ".join(map(str, excluded_player_names[:5]))
        excluded_text = (
            f"{preview}, and {excluded_player_count - 5} others"
        )

    formula_text = (
        "Negative percentage = negative impact ÷ "
        "(positive contribution + negative impact)."
    )

    if share_change > 0.05:
        direction_text = (
            f"The negative share **increased by {share_change:.1f} "
            "percentage points**, from "
            f"**{before['negative_share']:.1f}%** to "
            f"**{after['negative_share']:.1f}%**."
        )

        if positive_reduction_rate > negative_reduction_rate:
            if negative_removed > 0:
                raw_negative_note = (
                    "Although the raw negative impact also decreased, it "
                    "became a larger share of the smaller remaining total."
                )
            else:
                raw_negative_note = (
                    "The raw negative impact did not increase; it stayed the "
                    "same but became a larger share of the smaller remaining "
                    "total."
                )

            reason_text = (
                "This happened because the exclusions removed a larger "
                "proportion of positive contribution than negative impact. "
                f"Positive contribution fell by "
                f"**{positive_reduction_rate:.1f}%**, while negative impact "
                f"fell by **{negative_reduction_rate:.1f}%**. "
                f"{raw_negative_note}"
            )
        else:
            reason_text = (
                "The remaining score mix became more negative. The raw "
                "values and their relative changes are shown below; the "
                "percentage rose because negative impact occupies a larger "
                "part of the remaining positive-plus-negative total."
            )

    elif share_change < -0.05:
        direction_text = (
            "The premise does not match the current selection: the negative "
            f"share **decreased by {abs(share_change):.1f} percentage "
            f"points**, from **{before['negative_share']:.1f}%** to "
            f"**{after['negative_share']:.1f}%**."
        )
        reason_text = (
            "The exclusions removed a larger proportion of negative impact "
            "than positive contribution. "
            f"Negative impact fell by **{negative_reduction_rate:.1f}%**, "
            f"while positive contribution fell by "
            f"**{positive_reduction_rate:.1f}%**."
        )

    else:
        direction_text = (
            "The negative share is effectively unchanged at "
            f"**{after['negative_share']:.1f}%** "
            f"({share_change:+.1f} percentage points)."
        )
        reason_text = (
            "Positive contribution and negative impact changed in nearly "
            "the same proportion, so the balance between the two sides "
            "remained stable."
        )

    return (
        f"After excluding **{excluded_player_count} player(s)**"
        f"{period_text} — **{excluded_text}** — {direction_text}\n\n"
        f"- **Positive contribution:** "
        f"{format_score(before['positive'])} → "
        f"{format_score(after['positive'])} "
        f"(removed {format_score(positive_removed)}, "
        f"{positive_reduction_rate:.1f}%)\n"
        f"- **Negative impact:** "
        f"{format_score(before['negative'])} → "
        f"{format_score(after['negative'])} "
        f"(removed {format_score(negative_removed)}, "
        f"{negative_reduction_rate:.1f}%)\n\n"
        f"{reason_text}\n\n"
        f"{formula_text}"
    )


def explain_top_contributors(
    data,
    svs_period=None,
    alliance_names=None,
):
    """
    Rank the strongest player contributors within each alliance currently
    included by the dashboard filters.

    The ranking uses player net score. For players with positive net scores,
    contribution share is measured against the alliance's total positive net
    score in the current filter scope.
    """
    required_columns = {
        "alliance",
        "player_name",
        "score_gained",
        "score_lost",
        "net_score",
    }
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        return (
            "This explanation cannot be calculated because the current data "
            f"is missing: {missing_text}."
        )

    working_df = data[
        [
            "alliance",
            "player_name",
            "score_gained",
            "score_lost",
            "net_score",
        ]
    ].copy()

    for column in ["score_gained", "score_lost", "net_score"]:
        working_df[column] = pd.to_numeric(
            working_df[column],
            errors="coerce",
        )

    working_df = working_df.dropna(
        subset=["alliance", "player_name", "net_score"]
    )

    if alliance_names:
        requested = {str(name).casefold() for name in alliance_names}
        available_lookup = {
            str(name).casefold(): str(name)
            for name in working_df["alliance"].dropna().unique()
        }
        matched = [
            available_lookup[name]
            for name in requested
            if name in available_lookup
        ]

        if not matched:
            named_text = ", ".join(
                f"**{name}**" for name in alliance_names
            )
            return (
                f"I recognized {named_text}, but it is not included in the "
                "current alliance filter. Add it in the sidebar, then ask "
                "again."
            )

        working_df = working_df[
            working_df["alliance"].astype(str).str.casefold().isin(
                {name.casefold() for name in matched}
            )
        ].copy()

    if working_df.empty:
        return (
            "There is no player score data in the current filter scope. "
            "Select at least one alliance and a net-status option, then try "
            "again."
        )

    # Grouping keeps the answer correct even if a player appears in more than
    # one row within the selected scope.
    player_summary = (
        working_df
        .groupby(["alliance", "player_name"], as_index=False)
        .agg(
            score_gained=("score_gained", "sum"),
            score_lost=("score_lost", "sum"),
            net_score=("net_score", "sum"),
        )
    )

    alliances = sorted(
        player_summary["alliance"].dropna().astype(str).unique().tolist()
    )

    if not alliances:
        return (
            "No alliance is available in the current filter scope. Select "
            "at least one alliance and try again."
        )

    period_text = f" for **{svs_period}**" if svs_period else ""
    single_alliance = len(alliances) == 1
    top_n = 5 if single_alliance else 3
    sections = []

    for alliance in alliances:
        alliance_players = player_summary[
            player_summary["alliance"].astype(str) == alliance
        ].copy()

        alliance_players = alliance_players.sort_values(
            ["net_score", "score_gained", "player_name"],
            ascending=[False, False, True],
        )

        positive_players = alliance_players[
            alliance_players["net_score"] > 0
        ].copy()
        alliance_positive_total = positive_players["net_score"].sum()
        alliance_net_total = alliance_players["net_score"].sum()

        if not positive_players.empty:
            ranked_players = positive_players.head(top_n).copy()
            ranking_description = "positive contributors by net score"
        else:
            ranked_players = alliance_players.head(top_n).copy()
            ranking_description = (
                "players with the highest net scores; no player has a "
                "positive net score in this scope"
            )

        lines = [
            f"**{alliance}** — {ranking_description}:"
        ]

        for rank, row in enumerate(
            ranked_players.itertuples(index=False),
            start=1,
        ):
            score_details = (
                f"net **{format_signed_score(row.net_score)}** "
                f"(gained {format_score(row.score_gained)}, "
                f"lost {format_score(row.score_lost)})"
            )

            if row.net_score > 0 and alliance_positive_total > 0:
                share = row.net_score / alliance_positive_total * 100
                score_details += (
                    f", **{share:.1f}%** of the alliance's positive "
                    "contribution"
                )

            lines.append(
                f"{rank}. **{row.player_name}** — {score_details}"
            )

        if not positive_players.empty:
            ranked_positive_total = ranked_players["net_score"].sum()
            ranked_share = (
                ranked_positive_total / alliance_positive_total * 100
                if alliance_positive_total > 0
                else 0
            )
            lines.append(
                f"The listed player(s) account for **{ranked_share:.1f}%** "
                "of this alliance's positive contribution in the current "
                "filter scope."
            )

        lines.append(
            f"Alliance total net score in this scope: "
            f"**{format_signed_score(alliance_net_total)}**."
        )
        sections.append("\n".join(lines))

    if single_alliance:
        introduction = (
            f"The strongest contributors{period_text} are ranked by "
            "**player net score**."
        )
    else:
        introduction = (
            f"Because **{len(alliances)} alliances** are selected"
            f"{period_text}, the dashboard shows the top **{top_n}** "
            "contributors within each alliance. Players are ranked by "
            "**player net score**."
        )

    return introduction + "\n\n" + "\n\n".join(sections)


def answer_dashboard_question(
    question,
    data,
    svs_period=None,
    selected_player_names=None,
    known_alliance_names=None,
):
    """Route suggested and free-text questions to supported analyses."""
    normalized_question = normalize_question_text(question)

    if known_alliance_names is None:
        known_alliance_names = (
            data["alliance"].dropna().unique().tolist()
            if "alliance" in data.columns
            else []
        )

    mentioned_alliances = extract_alliance_names_from_question(
        question,
        known_alliance_names,
    )

    # Exact suggested questions remain deterministic.
    if question == QUESTION_NET_VS_POSITIVE:
        return explain_net_vs_positive_ranking(data, svs_period)

    if question == QUESTION_EXCLUSION_IMPACT:
        return explain_exclusion_impact(
            data,
            selected_player_names,
            svs_period,
        )

    if question == QUESTION_NEGATIVE_PERCENTAGE:
        return explain_negative_percentage_change(
            data,
            selected_player_names,
            svs_period,
        )

    if question == QUESTION_TOP_CONTRIBUTORS:
        return explain_top_contributors(data, svs_period)

    exclusion_terms = {
        "exclude",
        "excluded",
        "excluding",
        "without",
        "remove",
        "removed",
        "removing",
        "except",
    }
    has_exclusion_term = any(
        term in normalized_question.split()
        for term in exclusion_terms
    )

    # A named-alliance exclusion is checked before the generic player-
    # exclusion route so "What changed after excluding TDA?" is interpreted
    # as an alliance calculation, not the Player Selection widget.
    if has_exclusion_term and mentioned_alliances and (
        "alliance" in normalized_question
        or "net" in normalized_question
        or "score" in normalized_question
        or "total" in normalized_question
        or "change" in normalized_question
    ):
        return explain_total_net_excluding_alliances(
            data,
            mentioned_alliances,
            svs_period,
        )

    if has_exclusion_term and (
        "net score" in normalized_question
        or "total net" in normalized_question
    ) and not mentioned_alliances:
        available_text = ", ".join(
            map(str, known_alliance_names)
        )
        return (
            "I understood that you want a total net score after excluding "
            "an alliance, but I could not identify the alliance name. "
            f"Available alliance names for this SVS period are: "
            f"**{available_text}**."
        )

    # Natural-language paraphrases of the existing analyses.
    # Compare the net-score leader with positive-contribution ranking.
    # Users do not have to include the word "alliance" explicitly; phrases
    # such as "net-score leader" or "top net score" imply it.
    ranking_subject_terms = [
        "alliance",
        "leader",
        "top net",
        "highest net",
        "first in net",
        "net score winner",
    ]
    ranking_comparison_terms = [
        "positive contribution",
        "positive rank",
        "positive ranking",
        "first in positive",
        "top in positive",
    ]

    if (
        "net" in normalized_question
        and any(
            term in normalized_question
            for term in ranking_subject_terms
        )
        and (
            any(
                term in normalized_question
                for term in ranking_comparison_terms
            )
            or (
                "positive" in normalized_question
                and any(
                    term in normalized_question
                    for term in ["rank", "ranking", "first", "top"]
                )
            )
        )
    ):
        return explain_net_vs_positive_ranking(data, svs_period)

    if (
        has_exclusion_term
        and (
            "player" in normalized_question
            or "selected" in normalized_question
        )
        and (
            "change" in normalized_question
            or "impact" in normalized_question
            or "happen" in normalized_question
            or "result" in normalized_question
        )
    ):
        return explain_exclusion_impact(
            data,
            selected_player_names,
            svs_period,
        )

    if (
        "negative" in normalized_question
        and any(
            term in normalized_question
            for term in ["percentage", "percent", "share", "ratio"]
        )
        and any(
            term in normalized_question
            for term in ["increase", "increased", "rise", "rose", "change"]
        )
    ):
        return explain_negative_percentage_change(
            data,
            selected_player_names,
            svs_period,
        )

    if (
        any(term in normalized_question for term in ["player", "who"])
        and any(
            term in normalized_question
            for term in [
                "contribut",
                "top",
                "best",
                "highest net",
                "most",
            ]
        )
        and (
            "alliance" in normalized_question
            or mentioned_alliances
        )
    ):
        return explain_top_contributors(
            data,
            svs_period,
            alliance_names=mentioned_alliances or None,
        )

    return (
        "I could not map that question to a supported dashboard analysis yet. "
        "This version uses rule-based matching rather than an AI API. Try one "
        "of these forms:\n\n"
        "- **What is the total net score without TDA?**\n"
        "- **Who contributed most in SnS?**\n"
        "- **How did excluding selected players change the result?**\n"
        "- **Why did the negative share rise?**\n"
        "- **Why is the net-score leader not first in positive contribution?**"
    )


@st.dialog("Ask the Dashboard", width="large")
def ask_dashboard_dialog():
    alliance_scope = ", ".join(map(str, selected_alliances)) or "None"
    status_scope = ", ".join(map(str, selected_net_status)) or "None"
    current_selected_players = get_current_selected_player_names(
        filtered_df
    )
    total_players_in_scope = (
        filtered_df["player_name"].nunique()
        if "player_name" in filtered_df.columns
        else 0
    )

    st.caption(
        f"Current scope — SVS: {selected_svs} | "
        f"Alliances: {alliance_scope} | Net status: {status_scope} | "
        f"Included players: {len(current_selected_players)}/"
        f"{total_players_in_scope}"
    )

    suggested_question = st.selectbox(
        "Choose a suggested question",
        SUGGESTED_QUESTIONS,
    )

    custom_question = ""

    if suggested_question == QUESTION_CUSTOM:
        st.caption(
            "Free-text questions currently use rule-based matching. Supported "
            "topics include alliance ranking, player exclusions, negative "
            "share, top contributors, and total net score without named "
            "alliances."
        )
        custom_question = st.text_area(
            "Enter your question",
            placeholder=(
                "Examples: What is the total net score without TDA? "
                "Who contributed most in SnS?"
            ),
        )

    question = (
        custom_question.strip()
        if suggested_question == QUESTION_CUSTOM
        else suggested_question
    )

    if st.button(
        "Explain",
        type="primary",
        disabled=not question,
    ):
        answer = answer_dashboard_question(
            question,
            filtered_df,
            selected_svs,
            current_selected_players,
            alliance_options,
        )
        st.markdown("### Explanation")
        st.markdown(answer)


if st.button("💬 Ask the Dashboard", type="primary"):
    ask_dashboard_dialog()


# Tabs
tab_overview, tab_alliance, tab_players, tab_contribution, tab_player_selection = st.tabs(
    [
        t("overview"),
        t("alliance_summary"),
        t("player_data"),
        t("contribution_insight"),
        t("player_selection_insight"),
    ]
)

# Main metrics & scatter plot
with tab_overview:
    st.subheader(t("overview"))

    # Full-server totals for the selected SVS period only.
    # Alliance and net-status filters do not affect these Overview metrics.
    server_total_players = period_df["player_name"].nunique()
    server_total_gained = period_df["score_gained"].sum()
    server_total_lost = period_df["score_lost"].sum()
    server_total_net = period_df["net_score"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 2])

    col1.metric(t("svs_period"), selected_svs)
    col2.metric(t("players"), f"{server_total_players:,}")
    col3.metric(t("score_gained"), f"{server_total_gained:,.0f}")
    col4.metric(t("score_lost"), f"{server_total_lost:,.0f}")
    col5.metric(t("net_score"), f"{server_total_net:,.0f}")

    st.divider()

    st.subheader(t("score_gained_vs_net_score"))
    st.caption(t("scatter_chart_caption"))

    # Create translated display values without changing the original data
    scatter_df = filtered_df.copy()

    scatter_df["net_status_display"] = (
        scatter_df["net_status"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({
            "positive": t("positive"),
            "negative": t("negative"),
        })
        .fillna(scatter_df["net_status"])
    )

    fig_scatter = px.scatter(
        scatter_df,
        x="score_gained",
        y="net_score",
        color="alliance",
        hover_name="player_name",
        custom_data=[
            "alliance",
            "score_gained",
            "score_lost",
            "net_score",
            "competition_rank",
            "net_status_display"
        ],
        labels={
            "alliance": t("alliance"),
            "score_gained": t("score_gained"),
            "net_score": t("net_score"),
        },
        title=None
    )

    fig_scatter.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            + t("alliance") + ": %{customdata[0]}<br>"
            + t("score_gained") + ": %{customdata[1]:,.0f}<br>"
            + t("score_lost") + ": %{customdata[2]:,.0f}<br>"
            + t("net_score") + ": %{customdata[3]:,.0f}<br>"
            + t("svs_rank") + ": %{customdata[4]}<br>"
            + t("status") + ": %{customdata[5]}"
            + "<extra></extra>"
        )
    )

    fig_scatter.add_hline(
        y=0,
        line_dash="dash",
        annotation_text=t("zero_net_score"),
        annotation_position="bottom right"
    )

    fig_scatter.update_layout(
        xaxis_title=t("score_gained"),
        yaxis_title=t("net_score"),
        legend_title_text=t("alliance"),
        height=600
    )

    st.plotly_chart(
        fig_scatter,
        use_container_width=True
    )

## Alliance Summary ##
with tab_alliance:
    st.subheader(t("alliance_summary"))
    st.caption(
        t("alliance_summary_caption")
    )

    alliance_summary = make_alliance_summary(filtered_df)

    st.dataframe(
        alliance_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "alliance": st.column_config.TextColumn(t("alliance"), width="small"),
            "players": st.column_config.NumberColumn(t("players"), format="%d", width="small"),
            "positive_players": st.column_config.NumberColumn(t("positive_players"), format="%d"),
            "negative_players": st.column_config.NumberColumn(t("negative_players"), format="%d"),
            "total_score_gained": st.column_config.NumberColumn(t("score_gained"), format="%,.0f"),
            "total_score_lost": st.column_config.NumberColumn(t("score_lost"), format="%,.0f"),
            "total_net_score": st.column_config.NumberColumn(t("net_score"), format="%,.0f"),
            "average_net_score": st.column_config.NumberColumn(t("net_per_player"), format="%,.0f", width="medium"),
        }
    )

    st.divider()

    # Total Net Score by Alliance
    st.subheader(t("total_net_score_by_alliance"))
    st.caption(t("total_net_score_by_alliance_caption"))

    fig_alliance_net = px.bar(
        alliance_summary,
        x="alliance",
        y="total_net_score",
        text_auto=True,
        labels={
            "alliance": t("alliance"),
            "total_net_score": t("total_net_score"),
        },
        title=None
    )

    fig_alliance_net.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            + t("total_net_score") + ": %{y:,.0f}"
            + "<extra></extra>"
        )
    )

    fig_alliance_net.update_layout(
        xaxis_title=t("alliance"),
        yaxis_title=t("total_net_score"),
        height=500
    )

    st.plotly_chart(
        fig_alliance_net,
        use_container_width=True
    )

    st.divider()

    # Net Score per Player by Alliance
    st.subheader(t("net_score_per_player_by_alliance"))
    st.caption(
        t("net_score_per_player_by_alliance_caption")
    )

    net_per_player_df = alliance_summary.copy()

    net_per_player_df["net_score_per_player"] = (
        net_per_player_df["total_net_score"]
        / net_per_player_df["players"]
    )

    net_per_player_df = net_per_player_df.sort_values(
        "net_score_per_player",
        ascending=False
    )

    fig_net_per_player = px.bar(
        net_per_player_df,
        x="alliance",
        y="net_score_per_player",
        text_auto=True,
        labels={
            "alliance": t("alliance"),
            "net_score_per_player": t("net_per_player"),
        },
        title=None
    )

    fig_net_per_player.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            + t("net_per_player")
            + ": %{y:,.0f}"
            + "<extra></extra>"
        )
    )

    fig_net_per_player.update_layout(
        xaxis_title=t("alliance"),
        yaxis_title=t("net_per_player"),
        height=500
    )

    st.plotly_chart(
        fig_net_per_player,
        use_container_width=True
    )

## Player Data ##
with tab_players:
    st.subheader(t("player_rankings"))

    ranking_options = [
        "top_10_net_score",
        "bottom_10_net_score",
        "top_10_score_gained",
        "top_10_score_lost",
    ]

    ranking_option = st.selectbox(
        t("select_ranking_view"),
        options=ranking_options,
        format_func=t
    )

    ranking_source = filtered_df.copy()

    # Use negative values so score lost bars extend below zero
    ranking_source["score_lost_negative"] = (
        ranking_source["score_lost"] * -1
    )

    if ranking_option == "top_10_net_score":
        sort_column = "net_score"
        sort_ascending = False
        y_column = "net_score"

    elif ranking_option == "bottom_10_net_score":
        sort_column = "net_score"
        sort_ascending = True
        y_column = "net_score"

    elif ranking_option == "top_10_score_gained":
        sort_column = "score_gained"
        sort_ascending = False
        y_column = "score_gained"

    else:
        sort_column = "score_lost"
        sort_ascending = False
        y_column = "score_lost_negative"

    chart_title = t(ranking_option)

    ranking_df = (
        ranking_source
        .sort_values(
            sort_column,
            ascending=sort_ascending,
            na_position="last"
        )
        .head(10)
    )

    fig_ranking = px.bar(
        ranking_df,
        x="player_name",
        y=y_column,
        color="alliance",
        text_auto=True,
        labels={
            "player_name": t("player"),
            "alliance": t("alliance"),
            y_column: t("score"),
        },
        title=chart_title
    )

    fig_ranking.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            + t("score")
            + ": %{y:,.0f}"
            + "<extra></extra>"
        )
    )

    fig_ranking.update_layout(
        xaxis_title=t("player"),
        yaxis_title=t("score"),
        legend_title_text=t("alliance"),
        xaxis_tickangle=-45
    )

    st.plotly_chart(
        fig_ranking,
        use_container_width=True
    )

    st.info(t("ranking_chart_guide"))

    st.divider()

    st.subheader(t("player_data"))
    st.caption(t("player_data_caption"))

    # Player Display
    player_table_source = filtered_df.copy()
    player_table_source["score_lost"] = player_table_source["score_lost"] * -1

    player_table_source["net_status_display"] = (
        player_table_source["net_status"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({
            "positive": t("positive"),
            "negative": t("negative"),
        })
        .fillna(player_table_source["net_status"])
    )

    table_sort_column = sort_column
    table_sort_ascending = sort_ascending

    if ranking_option == "top_10_score_lost":
        table_sort_column = "score_lost"
        table_sort_ascending = True
    player_display_df = (
        player_table_source
        .sort_values(
            table_sort_column,
            ascending=table_sort_ascending,
            na_position="last"
        )
        [
            [
                "competition_rank",
                "alliance",
                "player_name",
                "score_gained",
                "score_lost",
                "net_score",
                "net_status_display"
            ]
        ]
    )

    st.dataframe(
        player_display_df,
        use_container_width=True,
        hide_index=True,
        placeholder="-",
        column_config={
            "competition_rank": st.column_config.NumberColumn(
                t("svs_rank"),
                format="%d"
            ),
            "alliance": st.column_config.TextColumn(
                t("alliance")
            ),
           "player_name": st.column_config.TextColumn(
                t("players")
            ),
            "score_gained": st.column_config.NumberColumn(
                t("score_gained"),
                format="%,.0f"
            ),
            "score_lost": st.column_config.NumberColumn(
                t("score_lost"),
                format="%,.0f"
            ),
            "net_score": st.column_config.NumberColumn(
                 t("net_score"),
                format="%,.0f"
            ),
            "net_status_display": st.column_config.TextColumn(
                t("status")
            ),
        }
    )

## Contribution by Alliance ##
with tab_contribution:
    st.header(t("contribution_insight"))
    st.caption(t("contribution_insight_caption"))

    # -----------------------------
    # Filtered metrics
    # -----------------------------
    filtered_total_players = filtered_df["player_name"].nunique()
    filtered_total_gained = filtered_df["score_gained"].sum()
    filtered_total_lost = filtered_df["score_lost"].sum()
    filtered_total_net = filtered_df["net_score"].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(t("filtered_players"), f"{filtered_total_players:,}")
    col2.metric(t("score_gained"), f"{filtered_total_gained:,.0f}")
    col3.metric(t("score_lost"), f"{filtered_total_lost:,.0f}")
    col4.metric(t("net_score"), f"{filtered_total_net:,.0f}")

    st.divider()

    # -----------------------------
    # Prepare contribution data
    # -----------------------------
    contribution_df = filtered_df.copy()

    # Positive contribution
    positive_df = contribution_df[contribution_df["net_score"] > 0].copy()

    positive_contribution = (
        positive_df
        .groupby("alliance", as_index=False)
        .agg(positive_net_score=("net_score", "sum"))
    )

    server_positive_total = positive_contribution["positive_net_score"].sum()

    if server_positive_total > 0:
        positive_contribution["positive_contribution_share"] = (
            positive_contribution["positive_net_score"] / server_positive_total * 100
        )
    else:
        positive_contribution["positive_contribution_share"] = 0

    positive_contribution = positive_contribution.sort_values(
        "positive_contribution_share",
        ascending=False
    )

    # Negative contribution
    negative_df = contribution_df[contribution_df["net_score"] < 0].copy()

    negative_contribution = (
        negative_df
        .groupby("alliance", as_index=False)
        .agg(negative_net_score=("net_score", "sum"))
    )

    negative_contribution["negative_net_score_abs"] = (
        negative_contribution["negative_net_score"].abs()
    )

    server_negative_total = negative_contribution["negative_net_score_abs"].sum()

    if server_negative_total > 0:
        negative_contribution["negative_contribution_share"] = (
            negative_contribution["negative_net_score_abs"] / server_negative_total * 100
        )
    else:
        negative_contribution["negative_contribution_share"] = 0

    negative_contribution = negative_contribution.sort_values(
        "negative_contribution_share",
        ascending=False
    )

    # -----------------------------
    # Main visual insight
    # -----------------------------
    st.markdown(t("contribution_share"))
    st.caption(t("contribution_share_caption"))

    col_chart_pos, col_chart_neg = st.columns(2)

    with col_chart_pos:
        st.markdown(t("positive_contribution"))


        if server_positive_total > 0:
            fig_positive_pie = px.pie(
                positive_contribution,
                names="alliance",
                values="positive_net_score",
                labels={
                    "alliance": t("alliance"),
                    "positive_net_score": t("positive_net"),
                },
                title=None
            )

            fig_positive_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    + t("positive_net")
                    + ": %{value:,.0f}<br>"
                    + t("share")
                    + ": %{percent}"
                    + "<extra></extra>"
                )
            )

            fig_positive_pie.update_layout(
                height=430,
                margin=dict(t=20, b=20, l=20, r=20),
                legend_title_text=t("alliance")
            )

            st.plotly_chart(
                fig_positive_pie,
                use_container_width=True
            )
        else:
            st.info(t("no_positive_net_score"))

    with col_chart_neg:
        st.markdown(t("negative_contribution"))

        if server_negative_total > 0:
            fig_negative_pie = px.pie(
                negative_contribution,
                names="alliance",
                values="negative_net_score_abs",
                labels={
                    "alliance": t("alliance"),
                    "negative_net_score_abs": t("negative_net"),
                },
                title=None
            )

            fig_negative_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    + t("negative_net")
                    + ": %{value:,.0f}<br>"
                    + t("share")
                    + ": %{percent}"
                    + "<extra></extra>"
                )
            )

            fig_negative_pie.update_layout(
                height=430,
                margin=dict(t=20, b=20, l=20, r=20),
                legend_title_text=t("alliance")
            )

            st.plotly_chart(
                fig_negative_pie,
                use_container_width=True
            )
        else:
            st.info(t("no_negative_net_score"))

    st.caption(t("negative_chart_explanation"))

    st.divider()

    # -----------------------------
    # Supporting tables
    # -----------------------------
    st.markdown(t("contribution_details"))
    st.caption(t("contribution_details_caption") )

    col_pos, col_neg = st.columns(2)

    with col_pos:
        st.markdown(t("positive_side"))

        display_positive = positive_contribution.copy()

        display_positive["positive_net_score"] = (
            display_positive["positive_net_score"].map("{:,.0f}".format)
        )

        display_positive["positive_contribution_share"] = (
            display_positive["positive_contribution_share"].map("{:.1f}%".format)
        )

        st.dataframe(
            positive_contribution,
            hide_index=True,
            use_container_width=True,
            column_config={
                "alliance": st.column_config.TextColumn(t("alliance")),
                "positive_net_score": st.column_config.NumberColumn(t("positive_net"), format="%,.0f"),
                "positive_contribution_share": st.column_config.NumberColumn(t("share_percent"), format="%.1f"),
            }
        )

    with col_neg:
        st.markdown(t("negative_side"))

        display_negative = negative_contribution.copy()

        display_negative["negative_net_score"] = (
            display_negative["negative_net_score"].map("{:,.0f}".format)
        )

        display_negative["negative_contribution_share"] = (
            display_negative["negative_contribution_share"].map("{:.1f}%".format)
        )

        display_negative = display_negative[
            [
                "alliance",
                "negative_net_score",
                "negative_contribution_share"
            ]
        ]

        st.dataframe(
            negative_contribution[
                [
                    "alliance",
                    "negative_net_score",
                    "negative_contribution_share"
                ]
            ],
            hide_index=True,
            use_container_width=True,
            column_config={
                "alliance": st.column_config.TextColumn(t("alliance")),
                "negative_net_score": st.column_config.NumberColumn(t("negative_net"), format="%,.0f"),
                "negative_contribution_share": st.column_config.NumberColumn(t("share_percent"), format="%.1f"),
            }
        )

    st.markdown(t("contribution_reading_guide"))

## Contribution by Player ##
with tab_player_selection:
    st.header(t("player_selection_insight"))
    st.caption(t("player_selection_insight_caption"))

    # Create containers to control display order
    selection_container = st.container()
    excluded_container = st.container()
    metric_container = st.container()
    contribution_container = st.container()
    summary_container = st.container()

    # Start from sidebar-filtered data
    player_scope_df = filtered_df.copy()

    # Player options from current sidebar filters
    player_options = sorted(player_scope_df["player_name"].dropna().unique())

    # -----------------------------
    # Player selection
    # -----------------------------
    with selection_container:
        st.subheader(t("choose_players_to_include"))
        st.caption(t("choose_players_caption"))

        with st.expander(t("selected_players"), expanded=True):
            selected_players = st.multiselect(
                t("select_players_to_include"),
                options=player_options,
                default=player_options
            )

    # Keep the current selection available to Ask the Dashboard, whose
    # dialog is defined earlier in the script than this tab's widgets.
    st.session_state["dashboard_selected_players"] = list(
        selected_players
    )

    # Data based on selected players
    selected_player_df = player_scope_df[
        player_scope_df["player_name"].isin(selected_players)
    ].copy()

    excluded_player_df = player_scope_df[
        ~player_scope_df["player_name"].isin(selected_players)
    ].copy()

    excluded_players = sorted(excluded_player_df["player_name"].dropna().unique())

    with excluded_container:
        with st.expander(t("excluded_players"), expanded=True):
            st.caption(t("excluded_players_caption"))

            if excluded_players:
                st.write(", ".join(excluded_players))
            else:
                st.success(t("no_excluded_players"))

    # -----------------------------
    # Server-level selected group impact
    # -----------------------------
    with metric_container:
        st.subheader(t("selected_group_impact"))
        st.caption(t("selected_group_impact_caption"))

        selected_players_count = selected_player_df["player_name"].nunique()
        excluded_players_count = excluded_player_df["player_name"].nunique()
        selected_score_gained = selected_player_df["score_gained"].sum()
        selected_score_lost = selected_player_df["score_lost"].sum()
        selected_net_score = selected_player_df["net_score"].sum()

        col1, col2, col3, col4, col5 = st.columns(5)
        col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 2])

        col1.metric(t("selected_players"), f"{selected_players_count:,}")
        col2.metric(t("excluded_players"), f"{excluded_players_count:,}")
        col3.metric(t("score_gained"), f"{selected_score_gained:,.0f}")
        col4.metric(t("score_lost"), f"{selected_score_lost:,.0f}")
        col5.metric(t("net_score"), f"{selected_net_score:,.0f}")

    # -----------------------------
    # Positive vs Negative Ratio
    # -----------------------------
    with contribution_container:
        st.divider()

        st.subheader(t("positive_negative_net_contribution"))
        st.caption(t("score_balance_caption"))

        # Keep stable internal status values for calculations and colors
        status_color_map = {
            "Positive": "#2ca02c",
            "Negative": "#d62728",
        }

        # Before exclusion: all players in current sidebar filters
        before_positive = player_scope_df.loc[
            player_scope_df["net_score"] > 0,
            "net_score"
        ].sum()

        before_negative = player_scope_df.loc[
            player_scope_df["net_score"] < 0,
            "net_score"
        ].abs().sum()

        # After exclusion: selected players only
        after_positive = selected_player_df.loc[
            selected_player_df["net_score"] > 0,
            "net_score"
        ].sum()

        after_negative = selected_player_df.loc[
            selected_player_df["net_score"] < 0,
            "net_score"
        ].abs().sum()

        before_ratio_df = pd.DataFrame({
            "status": ["Positive", "Negative"],
            "score": [before_positive, before_negative],
        })

        after_ratio_df = pd.DataFrame({
            "status": ["Positive", "Negative"],
            "score": [after_positive, after_negative],
        })

        # Translated labels for display
        status_translation = {
            "Positive": t("positive"),
            "Negative": t("negative"),
        }

        before_ratio_df["status_display"] = (
            before_ratio_df["status"].map(status_translation)
        )

        after_ratio_df["status_display"] = (
            after_ratio_df["status"].map(status_translation)
        )

        # The color map must now use the translated display values
        translated_status_color_map = {
            t("positive"): "#2ca02c",
            t("negative"): "#d62728",
        }

        translated_status_order = [
            t("positive"),
            t("negative"),
        ]

        selection_key = hash(tuple(sorted(selected_players)))

        col_before, col_after = st.columns(2)

        with col_before:
            st.markdown(t("before_exclusion"))
            st.caption(t("before_exclusion_caption"))

            if before_ratio_df["score"].sum() > 0:
                fig_before_ratio = px.pie(
                    before_ratio_df,
                    names="status_display",
                    values="score",
                    color="status_display",
                    category_orders={
                        "status_display": translated_status_order
                    },
                    color_discrete_map=translated_status_color_map,
                    labels={
                        "status_display": t("status"),
                        "score": t("score"),
                    },
                    title=None
                )

                fig_before_ratio.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        + t("score")
                        + ": %{value:,.0f}<br>"
                        + t("share")
                        + ": %{percent}"
                        + "<extra></extra>"
                    )
                )

                fig_before_ratio.update_layout(
                    height=430,
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend_title_text=t("status")
                )

                st.plotly_chart(
                    fig_before_ratio,
                    use_container_width=True,
                    key=f"before_positive_negative_ratio_{selection_key}"
                )
            else:
                st.info(t("no_score_data_before_exclusion"))

        with col_after:
            st.markdown(t("after_exclusion"))
            st.caption(t("after_exclusion_caption"))

            if after_ratio_df["score"].sum() > 0:
                fig_after_ratio = px.pie(
                    after_ratio_df,
                    names="status_display",
                    values="score",
                    color="status_display",
                    category_orders={
                        "status_display": translated_status_order
                    },
                    color_discrete_map=translated_status_color_map,
                    labels={
                        "status_display": t("status"),
                        "score": t("score"),
                    },
                    title=None
                )

                fig_after_ratio.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        + t("score")
                        + ": %{value:,.0f}<br>"
                        + t("share")
                        + ": %{percent}"
                        + "<extra></extra>"
                    )
                )

                fig_after_ratio.update_layout(
                    height=430,
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend_title_text=t("status")
                )

                st.plotly_chart(
                    fig_after_ratio,
                    use_container_width=True,
                    key=f"after_positive_negative_ratio_{selection_key}"
                )
            else:
                st.info(t("no_score_data_after_exclusion"))

    # -----------------------------
    # Alliance-level selected group impact
    # -----------------------------
    with summary_container:
        st.divider()

        st.subheader(t("alliance_impact_selected_players"))
        st.caption(t("alliance_impact_selected_players_caption"))

        if selected_player_df.empty:
            st.info(t("no_players_selected_alliance_summary"))
        else:
            selected_alliance_summary = make_alliance_summary(
                selected_player_df
            )

            fig_selected_alliance_net = px.bar(
                selected_alliance_summary,
                x="alliance",
                y="total_net_score",
                text_auto=True,
                labels={
                    "alliance": t("alliance"),
                    "total_net_score": t("total_net_score"),
                },
                title=None
            )

            fig_selected_alliance_net.update_traces(
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    + t("total_net_score")
                    + ": %{y:,.0f}"
                    + "<extra></extra>"
                )
            )

            fig_selected_alliance_net.update_layout(
                xaxis_title=t("alliance"),
                yaxis_title=t("total_net_score"),
                height=450,
                margin=dict(t=20, b=20, l=20, r=20)
            )

            st.plotly_chart(
                fig_selected_alliance_net,
                use_container_width=True,
                key=(
                    "player_selection_total_net_score_by_alliance_"
                    f"{selection_key}"
                )
            )

            st.dataframe(
                selected_alliance_summary,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "alliance": st.column_config.TextColumn(t("alliance")),
                    "players": st.column_config.NumberColumn(t("players"), format="%d"),
                    "positive_players": st.column_config.NumberColumn(t("positive_players"), format="%d"),
                    "negative_players": st.column_config.NumberColumn(t("negative_players"), format="%d"),
                    "total_score_gained": st.column_config.NumberColumn(t("score_gained"), format="%,.0f"),
                    "total_score_lost": st.column_config.NumberColumn(t("score_lost"), format="%,.0f"),
                    "total_net_score": st.column_config.NumberColumn(t("net_score"), format="%,.0f"),
                    "average_net_score": st.column_config.NumberColumn(t("net_per_player"), format="%,.0f"),
                }
            )
