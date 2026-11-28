#!/bin/sh
set -eu

source_script=$(CDPATH='' cd -- "$(dirname -- "$0")/../files" && pwd)/first-user-setup
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT
bin=$fixture/bin
mkdir "$bin" "$fixture/state" "$fixture/home"
export TEST_LOG="$fixture/calls"
export TEST_SCENARIO=success
sed "s|/var/lib/cip-core/|$fixture/state/|g; s|^home=/home/|home=$fixture/home/|" \
    "$source_script" > "$fixture/setup"

stub() {
    printf '#!/bin/sh\n%s\n' "$2" > "$bin/$1"
    chmod +x "$bin/$1"
}

stub id 'if [ "$#" = 1 ]; then echo 0; else cut -d: -f3 "$TEST_LOG.account.$2"; fi'
stub getent 'if [ "$TEST_SCENARIO" = existing ]; then exit 0; fi
[ "$1" = passwd ] && [ -f "$TEST_LOG.account.$2" ] && cat "$TEST_LOG.account.$2"'
stub adduser 'printf "adduser %s\n" "$*" >> "$TEST_LOG"
mkdir "$5"
printf "%s:x:1001:1001:%s,,,:%s:/bin/bash\n" "$6" "$3" "$5" > "$TEST_LOG.account.$6"
[ "$TEST_SCENARIO" != account_interrupted ]'
stub passwd 'if [ "$1" = -S ]; then
    if [ -e "$TEST_LOG.password" ]; then echo "$2 P"; else echo "$2 L"; fi
    exit 0
fi
printf "passwd %s\n" "$*" >> "$TEST_LOG"; [ "$TEST_SCENARIO" != password_failure ] && touch "$TEST_LOG.password"'

stub usermod '[ "$1" != -c ] || exit 0
printf "usermod %s\n" "$*" >> "$TEST_LOG"; [ "$TEST_SCENARIO" != admin_failure ]'

run() {
    expected=$1
    name=$2
    actual=0
    # Let script initialize the PTY before sending input or closing the pipe.
    {
        sleep 0.1
        # Early-exit cases can close the pipe before the fixture submits input.
        printf '%s\n' "$name" "${3:-}" 2>/dev/null || :
        sleep 0.1
    } |
        PATH="$bin:$PATH" script -qec "sh '$fixture/setup'" /dev/null > "$fixture/output" || actual=$?
    if [ "$expected" != "$actual" ]; then
        cat "$fixture/output" >&2
        exit 1
    fi
}

pending=$fixture/state/first-user-pending
complete=$fixture/state/first-user-complete

run 0 missingmarker
test ! -e "$TEST_LOG"
: > "$pending"
run 0 ''
run 0 'Invalid Name'
TEST_SCENARIO=existing run 0 existinguser
mkdir "$fixture/home/leftover"
run 0 leftover
test ! -e "$TEST_LOG"
test -f "$pending"
test ! -e "$complete"

TEST_SCENARIO=password_failure run 1 passwordfailure y
grep -Fq 'passwd passwordfailure' "$TEST_LOG"
! grep -q '^usermod ' "$TEST_LOG"
run 1 other-name
run 0 passwordfailure
test "$(grep -c '^adduser ' "$TEST_LOG")" = 1
test -f "$complete"
rm "$complete" "$TEST_LOG.password"
: > "$pending"
TEST_SCENARIO=admin_failure run 1 adminfailure y
grep -Fxq 'usermod -aG sudo adminfailure' "$TEST_LOG"
test -f "$pending"
test ! -e "$complete"

run 0 adminfailure
test "$(grep -c '^passwd adminfailure$' "$TEST_LOG")" = 1
test -f "$complete"
rm "$complete" "$TEST_LOG.password"
: > "$pending"
: > "$TEST_LOG"
run 0 test-user
grep -Eq "^adduser --disabled-password --gecos [a-f0-9-]+ --home $fixture/home/test-user test-user$" "$TEST_LOG"
grep -Fxq 'passwd test-user' "$TEST_LOG"
! grep -q '^usermod ' "$TEST_LOG"
test ! -e "$pending"
test -f "$complete"

: > "$TEST_LOG"
run 0 repeat
test ! -s "$TEST_LOG"
: > "$TEST_LOG"
rm -f "$TEST_LOG.password"
mv "$complete" "$pending"
run 0 admin-user y
printf '%s\n' 'passwd admin-user' 'usermod -aG sudo admin-user' > "$fixture/expected"
tail -n 2 "$TEST_LOG" | cmp - "$fixture/expected"
test ! -e "$pending"
test -f "$complete"
printf '%s\n' admin-required > "$pending"
rm -- "$complete" "$TEST_LOG.password"
: > "$TEST_LOG"
run 0 required-admin
printf '%s\n' 'passwd required-admin' 'usermod -aG sudo required-admin' > "$fixture/expected"
tail -n 2 "$TEST_LOG" | cmp - "$fixture/expected"
test ! -e "$pending"
test -f "$complete"
mv "$complete" "$pending"
rm "$TEST_LOG.password"
: > "$TEST_LOG"
TEST_SCENARIO=account_interrupted run 1 interrupted
test -f "$pending.intent"
test ! -e "$pending.account"
test ! -e "$TEST_LOG.password"
cp "$TEST_LOG.account.interrupted" "$fixture/original-account"
sed 's/:1001:1001:[^:]*:/:1001:1001:unrelated:/' "$fixture/original-account" > "$TEST_LOG.account.interrupted"
run 1 interrupted
test ! -e "$TEST_LOG.password"
cp "$fixture/original-account" "$TEST_LOG.account.interrupted"
run 0 interrupted
test "$(grep -c '^adduser ' "$TEST_LOG")" = 1
grep -Fxq 'usermod -aG sudo interrupted' "$TEST_LOG"
test ! -e "$pending.intent"
test -f "$complete"
printf '%s\n' 'First-user setup fixtures passed'
