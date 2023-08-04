<h1 align="center"> ıllıllı   🎀  𝑅𝐼𝒯𝑀  🎀   ıllıllı </h1>

В каждой папке находится самая новая версия ПО для всех устройств. Также можно установить все необходимые библиотеки командой <i>'pip install -r requirements.txt'</i>. Файл лежит в каждой директории, где есть необходимость что-то устанавливать.<br>
Что находится в папках:<br>

🔥 [src-doorway-2sensors](#src-doorway-2sensors) -- скрипт для рамки с двумя датчиками<br>
🔥 [src-box-invenory](#src-box-invenory) -- скрипт для модуля с разделением частей открытие/закрытие и инвентаризацией<br>
🔥 [src-big-box](#src-big-box) -- скрипт для большого шкафа<br>
🔥 [anntenna](#anntenna) -- скрипт для движения антенны (на ардуино)<br>
🔥 [other](#other) -- папка со всеми прочими вспомогательными скриптами<br>

<h2><a name="src-doorway-2sensors">src-doorway-2sensors</a></h2>

<h3>Алгоритм работы</h3>
Пересекается первый датчик, по нему определяется направление прохода, далее ждем несколько секунд, пока сканируются метки (в это время датчики могут срабатывать как угодно), после чего отсылается отчет и можно выходить из рамки. Следующий вход можно осуществлять ???
<h2><a name="src-box-invenory">src-box-invenory</a></h2>

Скрипт состоит из двух основных: main.py - открытие/закрытие, inventory.py - инвентаризация. 
Также есть запасной сценарий - nfc_check.py проверяет работоспрособность nfc, и , если он сломается, то выключаются основные скрипты и включается аварийный. При этом происходит открытие модуля.
На данный момент доступ к модулю реализован через проверку наличия пользователя в БД.<br>

Состояние модуля определяется по светодиоду, следующим образом<br>
🔴 - модуль закрыт<br>
🔴⚫️🔴 - карточка отсутствует в БД, доступ запрещен<br>
🟢 - модуль открыт<br>
🟢⚫️🟢 - модуль не закрылся до конца, нужно перезакрыть<br>
🟢🔴🟢 - nfc сломался<br>
<h2><a name="src-big-box">src-big-box</a></h2>
Скрипт для большого шкафа, логика аналогичная скрипту для модуля.

<h2><a name="anntenna">anntenna</a></h2>

<h3>Алгоритм работы</h3>
При подаче сигнала с пина отрабатывает функция прерывания, после чего начинается движение. Из центрального положения антенна двигается по рейке до начального положения, а дальше двигается в другую сторону с остановками (чтобы антенна нормально сканировала). Количество и время остановок регулируются в коде.
Если еще раз сработало прерывание и проезд антенны не был закончен, то все сбрасывается и начинается заново.

<h2><a name="other">other</a></h2>
Здесь собраны вспомогательные скрипты.

<h3>change_uid</h3>

Код применяется для изменения юидов модулей в соответствии с именем модуля. modules.xls - таблица с именами и юидами модулей - отсюда берутся юиды. В файл ip.txt записываются адреса модулей, для которых нужно поменять юиды.<br>

<h3>ping</h3>

Код для проверки соединения - если его нет, то происходит перезагрузка<br>

<h3>restart_daemon</h3>

Порядок работы:<br>
1) Файл restart_daemon.sh нужно положить в каждое устройство<br>
2) Запустить main_demonreboot.py. Он переберет все ip из файла ip.txt и сделает перезагрузку демона на всех устройствах<br>

<h3>updater</h3>

Для переноса папок файл main_transfer_dir.py. Необходимо прописать пути отправляемых папок и куда их отправлять. 
В ip.txt прописать все ip адреса.
