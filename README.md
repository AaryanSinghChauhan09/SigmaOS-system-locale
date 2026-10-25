    # SigmaOS-system-locale

    Locale & language selector

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/mintlocale

    ## Design principles applied
    - **Plan Before Apply**
- **Fail-Fast**
- **Idempotence**
- **KISS**
- **Deterministic Testing**

    ## Usage
    Verbs: `list, set, available, current`

    ```
    $ sigma-locale current --env env.json
$ sigma-locale list --gen locale.gen
$ sigma-locale available --catalog /usr/share/i18n/SUPPORTED
$ sigma-locale set --gen locale.gen --lang en_GB.UTF-8 --layout us \
      --plan plan.sh

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
