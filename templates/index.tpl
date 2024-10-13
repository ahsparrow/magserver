{% args dirs, logcounts, free %}
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CANBell</title>
    <link rel="stylesheet" href="/static/pure-min.css">
    <link rel="stylesheet" href="/static/style.css">
  </head>
  <body>
    <header>
      CANBell
    </header>
    <div class="pure-menu pure-menu-horizontal">
      <ul class="pure-menu-list">
        <li class="pure-menu-item pure-menu-selected">
          <a href="#" class="pure-menu-link">Logs</a>
        </li>
        <li class="pure-menu-item">
          <a href="/delays" class="pure-menu-link">Delays</a>
        </li>
      </ul>
    </div>
    <hr>
    <div class="contents">
      <form class="pure-form pure-form-aligned" action="/download">
        <legend>Session Logs</legend>
          {% for i in range(len(dirs)) %}
            <div class="pure-control-group">
              <label class="pure-radio">
                {{dirs[i]}} ({{logcounts[i]}})
              </label>
              <input type="radio" value="{{dirs[i]}}" {{"checked" if i == 0 else ""}} autocomplete="off" name="log">
            </div>
          {% endfor %}
          <div class="pure-controls">
            <button type="submit" class="pure-button pure-button-primary">Download</button>
          </div>
      </form>
      <div class="free-info">
        <p>{{free // 1000}} kB free</p>
      </div>
    </div>
  </body>
</html>

