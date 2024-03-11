#!/bin/bash


LOG_FILE="logs.log"


function log_info() {
    local message=$1
    echo "[INFO] $(date +"%Y-%m-%d %T") - $message" >> "$LOG_FILE"
}


function log_error() {
    local message=$1
    echo "[ERROR] $(date +"%Y-%m-%d %T") - $message" >> "$LOG_FILE"
}


function install_helm() {
    log_info "Installing helm..."
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh >> "$LOG_FILE" 2>&1
    rm get_helm.sh
}


function deploy_helm_chart() {
    if check_if_helmchart_installed; then
        echo "ERROR: Helm chart already installed. Please uninstall it first."
        log_error "Helm chart already installed. Please uninstall it first."
    else
        log_info "Deploying helm chart..."
        helm install survey ./survey >> "$LOG_FILE" 2>&1
    fi
}


function check_if_helmchart_installed() {
    if helm list | grep -q survey; then
        return 0
    else
        return 1
    fi
}


function uninstall_helm_chart() {
    if check_if_helmchart_installed; then
        log_info "Uninstalling helm chart..."
        helm uninstall survey >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function upgrade_helm_chart() {
    if check_if_helmchart_installed; then
        log_info "Upgrading helm chart..."
        helm upgrade survey ./survey >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function help_message() {
    echo "Usage: script.sh [OPTION]"
    echo "Options:"
    echo "  -helm      : to install helm (if not already installed)"
    echo "  -info      : to display the helm chart information"
    echo "  -deploy    : to deploy the helm chart"
    echo "  -uninstall : to uninstall the helm chart"
    echo "  -upgrade   : to upgrade the helm chart"
    echo "  -help      : to display the help message"
    echo "  -r         : to change the amount of replicas of the mongodb statefulset"
}


function change_replicas() {
    if check_if_helmchart_installed; then
        kubectl scale statefulset mongo-db -n survey-app --replicas="$1" >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function info_helm_chart() {
    if check_if_helmchart_installed; then
        kubectl get all -n survey-app
        # pass to logs
        kubectl get all -n survey-app >> "$LOG_FILE" 2>&1
    else
        echo "ERROR: Helm chart not installed. Please install it first."
        log_error "Helm chart not installed. Please install it first."
    fi
}


function main() {
    if [ $# -eq 0 ]; then
        help_message
        exit 1
    fi
    while getopts "h:i:d:u:U:h:r:" opt; do
        case $opt in
            h|helm) install_helm;;
            i|info) info_helm_chart;;
            d|deploy) deploy_helm_chart info_helm_chart;;
            u|uninstall) uninstall_helm_chart;;
            U|upgrade) upgrade_helm_chart info_helm_chart;;
            h|help) help_message;;
            r) change_replicas "$OPTARG" info_helm_chart;;
            *) echo "Invalid option: -$OPTARG" >&2; help_message; exit 1;;
        esac
    done
}


main "$@"