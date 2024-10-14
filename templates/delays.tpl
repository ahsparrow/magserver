{% args delays %}
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CANBell - Sensor Delays</title>
    <link rel="stylesheet" href="/static/pure-min.css">
    <link rel="stylesheet" href="/static/style.css">
  </head>
  <body>
    <header>
      CANBell
    </header>
    <div class="pure-menu pure-menu-horizontal">
      <ul class="pure-menu-list">
        <li class="pure-menu-item">
          <a href="/" class="pure-menu-link">Logs</a>
        </li>
        <li class="pure-menu-item pure-menu-selected">
          <a href="#" class="pure-menu-link">Delays</a>
        </li>
      </ul>
    </div>
    <hr>
    <div class="contents">
      <form class="pure-form pure-form-aligned" action="/delays" method="post">
        <fieldset>
          <legend>Sensor Delays (ms)</legend>
          {% for i in range(len(delays)) %}
            <div class="pure-control-group">
              <label>Bell #{{i + 1}}</label>
              <input type="text" inputmode="numeric" pattern="[0-9]{1,3}" required autocomplete="off" name="bell{{i}}" value={{delays[i]}} />
            </div>
          {% endfor %}
          <div class="pure-controls">
            <button name="action" value="ok" type="submit" class="pure-button pure-button-primary">OK</button>
            <button name="action" value="cancel" type="submit" class="pure-button pure-button-secondary">Cancel</button>
          </div>
        </fieldset>
      </form>
    </div>
  </body>
</html>

