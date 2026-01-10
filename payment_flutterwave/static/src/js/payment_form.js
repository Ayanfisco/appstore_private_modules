/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import paymentForm from "@payment/js/payment_form";

paymentForm.include({

    // Override to add Flutterwave-specific initialization
    async _processFlutterwavePayment(provider, paymentOptionId, paymentMethodCode, flow) {
        if (provider !== 'flutterwave') {
            return this._super(...arguments);
        }

        // Get rendering values from the server
        const processingValues = await this._rpc({
            route: '/payment/flutterwave/get_processing_values',
            params: {
                'provider_id': paymentOptionId,
                'payment_option_id': paymentOptionId,
                'reference_prefix': this.txContext.reference_prefix,
                'amount': this.txContext.amount,
                'currency_id': this.txContext.currency_id,
                'partner_id': this.txContext.partner_id,
                'flow': flow,
                'tokenization_requested': this.txContext.tokenization_requested,
                'landing_route': this.txContext.landing_route,
                'is_validation': this.txContext.is_validation,
            },
        });

        // Launch Flutterwave payment modal
        this._launchFlutterwaveModal(processingValues);
    },

    _launchFlutterwaveModal(processingValues) {
        const self = this;

        // Load Flutterwave inline script
        if (!window.FlutterwaveCheckout) {
            const script = document.createElement('script');
            script.src = 'https://checkout.flutterwave.com/v3.js';
            script.async = true;
            script.onload = function() {
                self._initializeFlutterwavePayment(processingValues);
            };
            document.head.appendChild(script);
        } else {
            this._initFlutterwavePayment(processingValues);
        }
    },

    _launchFlutterwaveModal(processingValues) {
        const self = this;

        // Prepare Flutterwave configuration
        const flwConfig = {
            public_key: processingValues.public_key,
            tx_ref: processingValues.tx_ref,
            amount: processingValues.amount,
            currency: processingValues.currency,
            payment_options: processingValues.payment_options,
            redirect_url: processingValues.redirect_url,
            customer: processingValues.customer,
            customizations: processingValues.customizations,
            meta: processingValues.meta,
            callback: function(response) {
                self._handleFlutterwaveCallback(response);
            },
            onclose: function() {
                self._handleFlutterwaveClose();
            }
        };

        // Add split payment if configured
        if (processingValues.payment_plan) {
            paymentData.payment_plan = processingValues.payment_plan;
        }

        // Show processing message
        this._displayNotification({
            type: 'info',
            title: _t("Redirecting to payment..."),
            message: _t("Please wait while we redirect you to Flutterwave payment page."),
        });

        try {
            // Initialize Flutterwave
            if (window.FlutterwaveCheckout) {
                FlutterwaveCheckout({
                    public_key: processingValues.public_key,
                    tx_ref: processingValues.tx_ref,
                    amount: processingValues.amount,
                    currency: processingValues.currency,
                    payment_options: processingValues.payment_options,
                    redirect_url: processingValues.redirect_url,
                    customer: processingValues.customer,
                    customizations: processingValues.customizations,
                    meta: processingValues.meta,
                    callback: function(response) {
                        self._handleFlutterwaveCallback(response);
                    },
                    onclose: function() {
                        self._handleFlutterwaveClose();
                    }
                });
        } else {
            // Script already loaded, launch modal
            FlutterwaveCheckout({
                public_key: processingValues.public_key,
                tx_ref: processingValues.tx_ref,
                amount: processingValues.amount,
                currency: processingValues.currency,
                payment_options: processingValues.payment_options,
                redirect_url: processingValues.redirect_url,
                customer: processingValues.customer,
                customizations: processingValues.customizations,
                meta: processingValues.meta,
                callback: function(response) {
                    self._handleFlutterwaveCallback(response);
                },
                onclose: function() {
                    self._displayError(
                        _t("Payment Cancelled"),
                        _t("The payment process was cancelled.")
                    );
                }
            });
        }
    },

    _handleFlutterwaveResponse(response) {
        const self = this;

        if (response.status === 'successful') {
            // Payment successful, verify on backend
            return this._rpc({
                route: '/payment/flutterwave/verify',
                params: {
                    'transaction_id': response.transaction_id,
                    'tx_ref': response.tx_ref,
                },
            }).then(function(result) {
                if (result.success) {
                    window.location.href = result.redirect_url || '/payment/status';
                } else {
                    self.displayNotification({
                        type: 'danger',
                        title: _t("Payment Error"),
                        message: result.error || _t("Payment verification failed"),
                    });
                }
            });
        } else if (response.status === 'cancelled') {
            // Payment was cancelled
            this.displayNotification({
                type: 'warning',
                title: _t("Payment Cancelled"),
                message: _t("You have cancelled the payment."),
            });
            window.location.href = '/shop/payment';
        } else {
            // Payment failed or other status
            this.displayNotification({
                type: 'danger',
                title: _t("Payment Error"),
                message: _t("Payment processing failed. Please try again."),
            });
        }
    },
});