"""
common_translations.py

Common translation set
for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
custom plugins

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

# Translations
# key : english, french, german, spanish, polish, brazilian portuguese, russian, chinese
# ----------------------------------------------

TRANSL = {
    # Roles
    "armycommander": ["commander", "commandant", "Kommandant", "comandante", "dowódca", "comandante", "командир", "指挥官"],
    "officer": ["squad leader", "officier", "Offizier", "líder de escuadrón", "dowódca drużyny", "líder de esquadrão", "офіцер", "小队长"],
    "rifleman": ["rifleman", "fusilier", "Schütze", "fusilero", "strzelec", "fuzileiro", "стрілець", "步枪手"],
    "assault": ["assault", "assault", "Sturmangreifer", "asalto", "szturmowiec", "assalto", "штурмовик", "突击手"],
    "automaticrifleman": ["automatic rifleman", "fusilier automatique", "Automatikgewehrschütze", "fusilero automático", "strzelec automatyczny", "fuzileiro automático", "автоматичний стрілець", "自动步枪手"],
    "medic": ["medic", "médecin", "Sanitäter", "médico", "medyk", "médico", "медик", "医务兵"],
    "support": ["support", "soutien", "Unterstützung", "apoyo", "wsparcie", "suporte", "підтримка", "支援兵"],
    "heavymachinegunner": ["heavy machinegunner", "mitrailleur", "Maschinengewehrschütze", "ametrallador pesado", "strzelec km", "metralhador pesado", "кулеметник", "重机枪手"],
    "antitank": ["antitank", "antichar", "Panzerabwehr", "antitanque", "przeciwpancerny", "antitanque", "протитанковий", "反坦克手"],
    "engineer": ["engineer", "ingénieur", "Pionier", "ingeniero", "inżynier", "engenheiro", "інженер", "工兵"],
    "tankcommander": ["tank commander", "commandant de char", "Panzerkommandant", "comandante de tanque", "dowódca czołgu", "comandante de tanque", "командир танка", "坦克指挥官"],
    "crewman": ["crewman", "équipier", "Besatzungsmitglied", "tripulante", "członek załogi", "tripulante", "член екіпажу", "乘员"],
    "spotter": ["spotter", "observateur", "Späher", "observador", "obserwator", "observador", "спостерігач", "侦察兵"],
    "sniper": ["sniper", "sniper", "Scharfschütze", "francotirador", "snajper", "atirador de elite", "снайпер", "狙击手"],
    "artilleryobserver": ["artillery observer", "observateur d'artillerie", "Artilleriebeobachter", "observador de artillería", "obserwator artylerii", "observador de artilharia", "артилерійський спостерігач", "炮兵观察员"],
    "artilleryengineer": ["artillery engineer", "ingénieur d'artillerie", "Artillerieingenieur", "ingeniero de artillería", "inżynier artylerii", "engenheiro de artilharia", "артилерійський інженер", "炮兵工程兵"],
    "artillerysupport": ["artillery support", "support d'artillerie", "Artillerieunterstützung", "apoyo de artillería", "wsparcie artylerii", "suporte de artilharia", "артилерійська підтримка", "炮兵支援"],

    # Teams
    "allies": ["Allies", "Alliés", "Alliierte", "Aliados", "Alianci", "Aliados", "Союзники", "盟军"],
    "axis": ["Axis", "Axe", "Achsenmächte", "Eje", "Oś", "Eixo", "Вісь", "轴心国"],

    # Stats
    "level": ["level", "niveau", "Level", "nivel", "poziom", "nível", "рівень", "等级"],
    "lvl": ["lvl", "niv", "Lvl", "nvl", "poz", "nvl", "рів", "级"],
    "combat": ["combat", "combat", "Kampfeffektivität", "combate", "walka", "combate", "бойова ефективність", "战斗"],
    "offense": ["attack", "attaque", "Angriff", "ataque", "atak", "ataque", "напад", "进攻"],
    "defense": ["defense", "défense", "Verteidigung", "defensa", "obrona", "defesa", "захист", "防御"],
    # support (already defined in Roles)
    "kills": ["kills", "kills", "Kills", "muertes", "zabójstwa", "abates", "вбивства", "击杀"],
    "deaths": ["deaths", "morts", "Deaths", "muertes", "śmierci", "mortes", "смерті", "死亡"],

    # Units
    "years": ["years", "années", "Jahre", "años", "lata", "anos", "роки", "年"],
    "monthes": ["monthes", "mois", "Monate", "meses", "miesiące", "meses", "місяці", "月"],
    "weeks": ["weeks", "semaines", "Wochen", "semanas", "tygodnie", "semanas", "тижні", "周"],
    "days": ["days", "jours", "Tage", "días", "dni", "dias", "дні", "天"],
    "hours": ["hours", "heures", "Stunden", "horas", "godziny", "horas", "години", "小时"],
    "minutes": ["minutes", "minutes", "Minuten", "minutos", "minuty", "minutos", "хвилини", "分钟"],
    "seconds": ["seconds", "secondes", "Sekunden", "segundos", "sekundy", "segundos", "секунди", "秒"],

    # !me (hooks_custom_chatcommands.py -> WARNING : circular import)
    # "nopunish": ["None ! Well done !", "Aucune ! Félicitations !", "Keiner! Gut gemacht!"],
    # "firsttimehere": ["first time here", "tu es venu(e) il y a", "zum ersten Mal hier"],
    # "gamesessions": ["game sessions", "sessions de jeu", "Spielesitzungen"],
    # "playedgames": ["played games", "parties jouées", "gespielte Spiele"],
    # "cumulatedplaytime": ["cumulated play time", "temps de jeu cumulé", "kumulierte Spielzeit"],
    # "averagesession": ["average session", "session moyenne", "Durchschnittliche Sitzung"],
    # "punishments": ["punishments", "punitions", "Strafen"],
    # "favoriteweapons": ["favorite weapons", "armes favorites", "Lieblingswaffen"],
    # "victims": ["victims", "victimes", "Opfer"],
    # "nemesis": ["nemesis", "nemesis", "Nemesis"],

    # Various
    "average": ["average", "moyenne", "Durchschnitt", "promedio", "średnia", "média", "середній", "平均"],
    # "averages": ["averages", "moyennes", "Durchschnittswerte"],
    "avg": ["avg", "moy", "avg", "prom", "śr", "méd", "сер", "均"],
    "distribution": ["distribution", "distribution", "Verteilung", "distribución", "dystrybucja", "distribuição", "розподіл", "分布"],
    "players": ["players", "joueurs", "Spieler", "jugadores", "gracze", "jogadores", "гравці", "玩家"],
    "score": ["score", "score", "Punktzahl", "puntuación", "wynik", "pontuação", "рахунок", "得分"],
    "stats": ["stats", "stats", "Statistiken", "estadísticas", "statystyki", "estatísticas", "статистика", "统计数据"],
    "total": ["total", "total", "Summe", "total", "suma", "total", "всього", "总计"],
    # "totals": ["totals", "totaux", "Gesamtsummen"],
    "tot": ["tot", "tot", "sum", "tot", "suma", "tot", "підсумок", "总"],
    # "difference": ["difference", "différence", "unterschied"],
    "officers": ["officers", "officiers", "Offiziere", "oficiales", "oficerowie", "oficiais", "офіцери", "军官"],
    "punishment": ["punishment", "punition", "Bestrafung", "castigo", "kara", "punição", "покарання", "惩罚"],
    "ratio": ["ratio", "ratio", "Verhältnis", "ratio", "stosunek", "razão", "співвідношення", "比率"],
    "victim": ["victim", "victime", "Opfer", "víctima", "ofiara", "vítima", "жертва", "受害者"],

    # automod_forbid_role.py
    "play_as": ["Play as", "A pris le rôle", "Spiele als", "Jugar como", "Graj jako", "Jogar como", "Грає як", "扮演"],
    "engaged_action": ["Engaged action :", "Action souhaitée :", "Laufende Aktion", "Acción realizada :", "Podjęte działanie :", "Ação engajada :", "Почата дія :", "进行的操作 :"],
    "reason": ["Reason :", "Raison :", "Ursache :", "Razón :", "Powód :", "Motivo :", "Причина :", "原因 :"],
    "action_result": ["Action result :", "Résultat de l'action :", "Ergebnis der Aktion", "Resultado de la acción :", "Wynik działania :", "Resultado da ação :", "Результат дії :", "操作结果 :"],
    "success": ["Success", "Réussite", "Erfolg", "Éxito", "Sukces", "Sucesso", "Успіх", "成功"],
    "failure": ["Failure", "Échec", "Fehler", "Fallo", "Niepowodzenie", "Falha", "Провал", "失败"],
    "unknown_action": ["Misconfigured action", "Action mal configurée", "Falsch konfigurierte Aktion", "Acción mal configurada", "Źle skonfigurowana akcja", "Ação mal configurada", "Невірно налаштована дія", "配置错误的操作"],
    "testmode": ["Test mode (no action)", "Mode test (aucune action)", "Testmodus (keine Aktion)", "Modo de prueba (sin acción)", "Tryb testowy (brak akcji)", "Modo de teste (sem ação)", "Тестовий режим (без дій)", "测试模式 (无操作)"],

    # watch_killrate.py
    "lastusedweapons": ["last used weapon(s)", "dernière(s) arme(s) utilisée(s)", "Zuletzt verwendete Waffe(n)", "última(s) arma(s) usada(s)", "ostatnia(e) użyta(e) broń(e)", "última(s) arma(s) utilizada(s)", "остання(і) використана(і) зброя", "最后使用的武器"],
    "noweaponfound": ["None (arti charger ? No new kill ?)", "Aucune (chargeur arti ? Pas de nouveau kill ?)", "Keiner (arti Ladegerät ? Kein neuer Kill ?)", "Ninguna (cargador de artillería ? No hay nueva muerte ?)", "Brak (ładowarka artylerii ? Brak nowego zabójstwa ?)", "Nenhuma (carregador de artilharia ? Sem novo abate ?)", "Немає (арти зарядний пристрій ? Немає нового вбивства ?)", "无 (火炮装填 ? 没有新的击杀 ?)"],

    # language_doorkeeper.py
    "expectedanswer": ["Expected answer", "Réponse attendue", "Erwartete Antwort", "Respuesta esperada", "Oczekiwana odpowiedź", "Resposta esperada", "Очікувана відповідь", "预期答案"],
    "receivedanswer": ["Received answer", "Réponse reçue", "Antwort erhalten", "Respuesta recibida", "Otrzymana odpowiedź", "Resposta recebida", "Отримана відповідь", "收到答案"],
    "blank": ["(blank)", "(rien)", "(leer)", "(en blanco)", "(puste)", "(em branco)", "(порожньо)", "(空白)"],
    "result": ["Result", "Résultat", "Ergebnis", "Resultado", "Wynik", "Resultado", "Результат", "结果"],
    "gaveavalidanswer": ["Gave a valid answer", "A bien répondu à la question", "Hat eine gute Antwort gegeben", "Dio una respuesta válida", "Udzielił poprawnej odpowiedzi", "Deu uma resposta válida", "Дав правильну відповідь", "给出了一个有效答案"],
    "disconnectedbeforetest": ["Disconnected before being tested.", "est parti avant la question.", "links vor der Frage.", "Se desconectó antes de ser probado.", "Odłączył się przed sprawdzeniem.", "Desconectou antes de ser testado.", "Відключився до перевірки.", "在测试前断开连接。"],
    "disconnectedbeforekick": ["left before the kick.", "est parti avant le kick.", "vor dem Ausschluss verlassen.", "Se fue antes de la expulsión.", "Odszedł przed wykopaniem.", "Saiu antes do kick.", "Пішов до кіка.", "在踢出前离开了。"],
    "hasbeenkicked": ["has been kicked.", "a été kické du serveur.", "wurde vom Server geworfen.", "ha sido expulsado.", "został wyrzucony.", "foi kickado.", "був кікнутий.", "已被踢出服务器。"],
    "flaggedvalid": ["has been flagged as valid.", "a été flaggé 'FR'.", "wurde als gültig gekennzeichnet.", "ha sido marcado como válido.", "został oznaczony jako ważny.", "foi sinalizado como válido.", "був позначений як дійсний.", "已被标记为有效。"],
    "processingtime": ["Processing time (secs) : ", "Temps de traitement (secs) : ", "Bearbeitungszeit (Sek.) : ", "Tiempo de procesamiento (segundos) : ", "Czas przetwarzania (sek.) : ", "Tempo de processamento (seg) : ", "Час обробки (сек) : ", "处理时间 (秒) : "]
}
