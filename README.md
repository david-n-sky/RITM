<h1 align="center"> R̶I̶T̶M̶ </h1>

В каждой папке находится самая новая версия ПО для всех устройств:
* [src-doorway-2sensors](#src-doorway-2sensors) -- скрипт для рамки с двумя датчиками
* [src-box-invenory](#src-box-invenory) -- скрипт для модуля с разделением частей открытие/закрытие и инвентаризацией
* src-big-box -- скрипт для большого шкафа
* anntenna -- скрипт для движения антенны (на ардуино)
* other -- папка со всеми прочими вспомогательными скриптами
---
<h2><a name="src-doorway-2sensors">src-doorway-2sensors</a></h2>

<h3>Алгоритм работы</h3>
Пересекается первый датчик, по нему определяется направление прохода, далее ждем несколько секунд, пока сканируются метки (в это время датчики могут срабатывать как угодно), после чего отсылается отчет и можно выходить из рамки.
___
<h2><a name="src-box-invenory">src-box-invenory</a></h2>

Скрипт состоит из двух основных: main.py - открытие/закрытие, inventory.py - инвентаризация. 
Также есть запасной сценарий - nfc_check.py проверяет работоспрособность nfc, и , если он сломается, то выключаются основные скрипты и включается аварийный. При этом происходит открытие модуля.
На данный момент доступ к модулю реализован через проверку наличия пользователя в БД.
<br>
Состояние модуля определяется по светодиоду, следующим образом<br>
🔴 - модуль закрыт<br>
🔴⚫️🔴 - карточка отсутствует в БД, доступ запрещен<br>
🟢 - модуль закрыт<br>
🟢⚫️🟢 - модуль не закрылся до конца, нужно перезакрыть<br>
🟢🔴🟢 - nfc сломался<br>
