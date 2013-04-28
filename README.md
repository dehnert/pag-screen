The `pag-screen` collection of scripts is based on Kevin Chen's `owl-screen`
and related programs from the `kchen` locker. They make it easier to maintain a
persistent `screen` session with tickets on a dialup like linerva.mit.edu or
athena.dialup.mit.edu.

The following scripts are available:
- *pag-screen*: runs screen with a copy of the Kerberos tickets in a new PAG,
  so that detaching and logging out leaves tickets and tokens intact
- *cont-renew-notify*: Renew a (renewable) ticket cache every hour, and zephyr
  when the tickets are approaching the end of their renewable lifetime


Additional features
-------------------

While `pag-screen` and `cont-renew-notify` are based on `owl-screen` and
`cont-renew-notify` in the `kchen` locker, they have some additional features:

- support for maintaining multiple sets of tickets (for example, for multiple
  realms or instances) in a `DIR` kerberos ccache
    - `pag-screen` will copy tickets to a `DIR` ccache if the original ccache
      is a `DIR` cache or `-d` is passed
    - `cont-renew-notify` will automatically renew all tickets in a `DIR`
      ccache
    - `renew-all` renews all tickets in a `DIR` ccache while ensuring that the
      default principal is unchanged
- `pag-screen` runs a shell instead of a zephyr client by default, which some
  users may find more convenient
- `cont-renew-notify` can print a message each time it does a renewal
- If `cont-renew-notify` is unable to send a notification zephyr the first
  time, it will stop after six tries, rather than spinning forever. (The
  version in the `kchen` locker tries to do this, but has a bug and will thus
  spin forever.)
